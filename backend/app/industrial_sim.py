"""Industrial protocol simulators for JARVIS testing.

Real, minimal, spec-correct test servers used to exercise the Modbus and MQTT
clients in ``industrial_service`` when no PLC or broker hardware is available.

Everything produced by these servers is **simulated** and must be reported as
such: they exist to prove the client code paths work, not to stand in for
hardware. The in-process Modbus register server is always available; the MQTT
broker is only registered when ``amqtt``/``hbmqtt`` is installed.
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from typing import Any, Optional

logger = logging.getLogger("jarvis.industrial_sim")


class ModbusTcpSimServer:
    """A small Modbus TCP slave implementing FC 01-06 and 15/16.

    Backed by in-memory coils and registers. Intended for tests and lab use.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 15020, unit_id: int = 1):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.coils: dict[int, bool] = {}
        self.discrete_inputs: dict[int, bool] = {}
        self.holding_registers: dict[int, int] = {}
        self.input_registers: dict[int, int] = {}
        self.request_count = 0
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    # -- lifecycle --------------------------------------------------------- #
    def start(self) -> dict[str, Any]:
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((self.host, self.port))
            self._server.listen(5)
            self._server.settimeout(1.0)
        except Exception as e:
            return {"success": False, "error": f"Could not bind simulator: {e}"}

        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="modbus-sim")
        self._thread.start()
        logger.info(f"[INDUSTRIAL_SIM] Modbus TCP simulator listening on {self.host}:{self.port}")
        return {"success": True, "host": self.host, "port": self.port, "simulated": True}

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("[INDUSTRIAL_SIM] Modbus TCP simulator stopped")

    @property
    def running(self) -> bool:
        return self._running

    # -- seeding ----------------------------------------------------------- #
    def seed(self, holding: dict[int, int] | None = None, coils: dict[int, bool] | None = None,
             discrete: dict[int, bool] | None = None, inputs: dict[int, int] | None = None):
        with self._lock:
            self.holding_registers.update(holding or {})
            self.coils.update(coils or {})
            self.discrete_inputs.update(discrete or {})
            self.input_registers.update(inputs or {})

    # -- server loop ------------------------------------------------------- #
    def _serve(self):
        while self._running and self._server:
            try:
                conn, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()

    def _handle(self, conn: socket.socket, addr):
        conn.settimeout(5.0)
        try:
            while self._running:
                header = self._recv(conn, 7)
                if not header:
                    break
                tid, proto, length, unit = struct.unpack(">HHHB", header)
                pdu = self._recv(conn, length - 1)
                if not pdu:
                    break
                with self._lock:
                    self.request_count += 1
                response_pdu = self._process(pdu)
                resp = struct.pack(">HHHB", tid, proto, len(response_pdu) + 1, unit) + response_pdu
                conn.sendall(resp)
        except Exception as e:
            logger.debug(f"[INDUSTRIAL_SIM] client handler ended: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _recv(conn: socket.socket, count: int) -> bytes:
        buf = b""
        while len(buf) < count:
            chunk = conn.recv(count - len(buf))
            if not chunk:
                return b""
            buf += chunk
        return buf

    def _process(self, pdu: bytes) -> bytes:
        fc = pdu[0]
        if fc == 0x01:  # read coils
            address, count = struct.unpack(">HH", pdu[1:5])
            bits = [self.coils.get(address + i, False) for i in range(count)]
            return self._pack_bits(fc, bits)
        if fc == 0x02:  # read discrete inputs
            address, count = struct.unpack(">HH", pdu[1:5])
            bits = [self.discrete_inputs.get(address + i, False) for i in range(count)]
            return self._pack_bits(fc, bits)
        if fc == 0x03:  # read holding registers
            address, count = struct.unpack(">HH", pdu[1:5])
            regs = [self.holding_registers.get(address + i, 0) for i in range(count)]
            return self._pack_regs(fc, regs)
        if fc == 0x04:  # read input registers
            address, count = struct.unpack(">HH", pdu[1:5])
            regs = [self.input_registers.get(address + i, 0) for i in range(count)]
            return self._pack_regs(fc, regs)
        if fc == 0x05:  # write single coil
            address, value = struct.unpack(">HH", pdu[1:5])
            self.coils[address] = value == 0xFF00
            return pdu[:5]
        if fc == 0x06:  # write single register
            address, value = struct.unpack(">HH", pdu[1:5])
            self.holding_registers[address] = value
            return pdu[:5]
        if fc == 0x0F:  # write multiple coils
            address, count, byte_count = struct.unpack(">HHB", pdu[1:6])
            payload = pdu[6:6 + byte_count]
            for i in range(count):
                byte = payload[i // 8]
                self.coils[address + i] = bool(byte & (1 << (i % 8)))
            return struct.pack(">BHH", fc, address, count)
        if fc == 0x10:  # write multiple registers
            address, count, byte_count = struct.unpack(">HHB", pdu[1:6])
            payload = pdu[6:6 + byte_count]
            regs = struct.unpack(f">{count}H", payload)
            for i, value in enumerate(regs):
                self.holding_registers[address + i] = value
            return struct.pack(">BHH", fc, address, count)
        # Illegal function
        return bytes([fc | 0x80, 0x01])

    @staticmethod
    def _pack_bits(fc: int, bits: list[bool]) -> bytes:
        byte_count = (len(bits) + 7) // 8
        payload = bytearray(byte_count)
        for i, bit in enumerate(bits):
            if bit:
                payload[i // 8] |= 1 << (i % 8)
        return bytes([fc, byte_count]) + bytes(payload)

    @staticmethod
    def _pack_regs(fc: int, regs: list[int]) -> bytes:
        payload = struct.pack(f">{len(regs)}H", *regs)
        return bytes([fc, len(payload)]) + payload

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "requests_served": self.request_count,
            "holding_registers": dict(self.holding_registers),
            "coils": dict(self.coils),
            "discrete_inputs": dict(self.discrete_inputs),
            "input_registers": dict(self.input_registers),
            "simulated": True,
        }


class MqttSimBroker:
    """Wrapper around an optional in-process MQTT broker.

    Only usable when ``amqtt`` (or ``hbmqtt``) is installed. When it is not,
    ``start()`` returns an explicit failure instead of pretending to run.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 11883):
        self.host = host
        self.port = port
        self._task = None
        self._loop = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @staticmethod
    def available() -> bool:
        try:
            import amqtt  # noqa: F401
            return True
        except ImportError:
            return False

    def start(self) -> dict[str, Any]:
        if not self.available():
            return {
                "success": False,
                "error": "MQTT simulator requires the 'amqtt' package (pip install amqtt). "
                         "The real MQTT client path needs paho-mqtt instead: pip install paho-mqtt",
                "simulated": True,
            }
        try:
            import asyncio
            from amqtt.broker import Broker  # type: ignore

            config = {
                "listeners": {"default": {"type": "tcp", "bind": f"{self.host}:{self.port}"}},
                "sys_interval": 0,
                "auth": {"allow-anonymous": True},
                "topic-check": {"enabled": False},
            }

            def run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                broker = Broker(config)
                self._task = loop.create_task(broker.start())
                self._running = True
                try:
                    loop.run_until_complete(self._task)
                except Exception as e:
                    logger.debug(f"[INDUSTRIAL_SIM] MQTT broker loop ended: {e}")

            self._thread = threading.Thread(target=run, daemon=True, name="mqtt-sim")
            self._thread.start()
            time.sleep(1.0)
            return {"success": True, "host": self.host, "port": self.port, "simulated": True}
        except Exception as e:
            return {"success": False, "error": str(e), "simulated": True}

    def stop(self):
        self._running = False
        if self._task and self._loop:
            try:
                self._loop.call_soon_threadsafe(self._task.cancel)
            except Exception:
                pass
        logger.info("[INDUSTRIAL_SIM] MQTT simulator stop requested")

    @property
    def running(self) -> bool:
        return self._running


_modbus_sim: ModbusTcpSimServer | None = None
_mqtt_sim: MqttSimBroker | None = None


def get_modbus_sim() -> ModbusTcpSimServer:
    """Process-wide Modbus simulator, seeded with a plausible robot cell."""
    global _modbus_sim
    if _modbus_sim is None:
        _modbus_sim = ModbusTcpSimServer()
        _modbus_sim.seed(
            holding={
                0: 125,    # conveyor_speed raw (scale 0.01 -> 1.25 m/s)
                1: 1,      # cell_state = running
                2: 42,     # part_counter
                3: 68,     # motor_temp_raw (degC)
                4: 1500,   # cycle_time_ms
            },
            discrete={0: True, 1: True},   # estop_ok, guard_closed
            coils={0: True, 1: False},     # conveyor_run, fault_reset
        )
    return _modbus_sim


def get_mqtt_sim() -> MqttSimBroker:
    global _mqtt_sim
    if _mqtt_sim is None:
        _mqtt_sim = MqttSimBroker()
    return _mqtt_sim
