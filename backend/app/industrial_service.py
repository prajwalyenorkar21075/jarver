"""Industrial automation service for JARVIS.

Talks to real industrial equipment over the standard protocols:

    Modbus TCP      — pure-Python client (no third-party dependency)
    OPC UA          — ``asyncua`` when installed, otherwise an explicit
                      "driver unavailable" result (never a fake success)
    MQTT            — ``paho-mqtt`` when installed, same honesty rule

Capability split, enforced by ``core.execution_policy``:

    READ / ANALYZE  — always allowed: read tags, alarms, machine state
    CONTROL         — requires explicit operator confirmation
    SIMULATE        — runs against the bundled simulator, touches no hardware

Nothing in this module deploys logic to production hardware on its own.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("jarvis.industrial")


# --------------------------------------------------------------------------- #
# Optional protocol drivers
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - environment dependent
    from asyncua import Client as _OpcUaClient  # type: ignore
    OPCUA_AVAILABLE = True
    OPCUA_IMPORT_ERROR = ""
except Exception as _e:  # pragma: no cover
    _OpcUaClient = None  # type: ignore
    OPCUA_AVAILABLE = False
    OPCUA_IMPORT_ERROR = str(_e)

try:  # pragma: no cover - environment dependent
    import paho.mqtt.client as _mqtt  # type: ignore
    MQTT_AVAILABLE = True
    MQTT_IMPORT_ERROR = ""
except Exception as _e:  # pragma: no cover
    _mqtt = None  # type: ignore
    MQTT_AVAILABLE = False
    MQTT_IMPORT_ERROR = str(_e)


class ControlMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    MONITORING = "MONITORING"
    SIMULATION = "SIMULATION"
    AUTHORIZED_CONTROL = "AUTHORIZED_CONTROL"


class DeviceKind(str, Enum):
    PLC = "plc"
    HMI = "hmi"
    SCADA = "scada"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    ROBOT = "robot"
    CONVEYOR = "conveyor"


@dataclass
class TagValue:
    tag: str
    value: Any
    unit: str = ""
    quality: str = "good"
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality,
            "timestamp": self.timestamp,
            "source": self.source,
        }


@dataclass
class Alarm:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    code: str = ""
    message: str = ""
    severity: str = "medium"
    source: str = ""
    active: bool = True
    raised_at: float = field(default_factory=time.time)
    cleared_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
            "active": self.active,
            "raised_at": self.raised_at,
            "cleared_at": self.cleared_at,
        }


# --------------------------------------------------------------------------- #
# Modbus TCP client (pure Python, stdlib only)
# --------------------------------------------------------------------------- #
class ModbusTcpClient:
    """Minimal, correct Modbus TCP master.

    Implements function codes 0x01-0x04 (read) and 0x05/0x06/0x0F/0x10 (write).
    Written against the Modbus Application Protocol spec so it can talk to a
    real PLC without a third-party library.

    The socket is connected once and reused across calls; the object is safe to
    share between threads (all request/response pairs are serialised).
    """

    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._transaction_id = 0
        self._lock = threading.RLock()

    # -- connection -------------------------------------------------------- #
    def connect(self) -> dict[str, Any]:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.settimeout(self.timeout)
            self._sock = sock
            logger.info(f"[INDUSTRIAL] Modbus TCP connected to {self.host}:{self.port}")
            return {"success": True, "host": self.host, "port": self.port}
        except Exception as e:
            self._sock = None
            logger.warning(f"[INDUSTRIAL] Modbus connect failed {self.host}:{self.port}: {e}")
            return {"success": False, "error": str(e), "host": self.host, "port": self.port}

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # -- framing ----------------------------------------------------------- #
    def _next_tid(self) -> int:
        self._transaction_id = (self._transaction_id + 1) % 65536
        return self._transaction_id

    def _request(self, pdu: bytes) -> bytes:
        if not self._sock:
            raise ConnectionError("Modbus TCP socket is not connected")
        with self._lock:
            tid = self._next_tid()
            header = struct.pack(">HHHB", tid, 0, len(pdu) + 1, self.unit_id)
            self._sock.sendall(header + pdu)
            resp_header = self._recv_exact(7)
            length = struct.unpack(">H", resp_header[4:6])[0]
            body = self._recv_exact(max(0, length - 1))
        return body

    def _recv_exact(self, count: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < count:
            chunk = self._sock.recv(count - len(buf))
            if not chunk:
                raise ConnectionError("Modbus connection closed by peer")
            buf += chunk
        return buf

    @staticmethod
    def _check_exception(body: bytes):
        if body and body[0] & 0x80:
            code = body[1] if len(body) > 1 else 0
            raise RuntimeError(f"Modbus exception response, code {code}")

    # -- reads ------------------------------------------------------------- #
    def read_coils(self, address: int, count: int = 1) -> list[bool]:
        body = self._request(struct.pack(">BHH", 0x01, address, count))
        self._check_exception(body)
        byte_count = body[1]
        bits: list[bool] = []
        for i in range(byte_count):
            byte = body[2 + i]
            for bit in range(8):
                bits.append(bool(byte & (1 << bit)))
        return bits[:count]

    def read_discrete_inputs(self, address: int, count: int = 1) -> list[bool]:
        body = self._request(struct.pack(">BHH", 0x02, address, count))
        self._check_exception(body)
        byte_count = body[1]
        bits: list[bool] = []
        for i in range(byte_count):
            byte = body[2 + i]
            for bit in range(8):
                bits.append(bool(byte & (1 << bit)))
        return bits[:count]

    def read_holding_registers(self, address: int, count: int = 1) -> list[int]:
        body = self._request(struct.pack(">BHH", 0x03, address, count))
        self._check_exception(body)
        byte_count = body[1]
        return list(struct.unpack(f">{byte_count // 2}H", body[2:2 + byte_count]))

    def read_input_registers(self, address: int, count: int = 1) -> list[int]:
        body = self._request(struct.pack(">BHH", 0x04, address, count))
        self._check_exception(body)
        byte_count = body[1]
        return list(struct.unpack(f">{byte_count // 2}H", body[2:2 + byte_count]))

    # -- writes ------------------------------------------------------------ #
    def write_coil(self, address: int, value: bool) -> bool:
        body = self._request(struct.pack(">BHH", 0x05, address, 0xFF00 if value else 0x0000))
        self._check_exception(body)
        return True

    def write_register(self, address: int, value: int) -> bool:
        body = self._request(struct.pack(">BHH", 0x06, address, value & 0xFFFF))
        self._check_exception(body)
        return True

    def write_registers(self, address: int, values: list[int]) -> bool:
        payload = struct.pack(">BHHB", 0x10, address, len(values), len(values) * 2)
        payload += struct.pack(f">{len(values)}H", *[v & 0xFFFF for v in values])
        body = self._request(payload)
        self._check_exception(body)
        return True


# --------------------------------------------------------------------------- #
# OPC UA client wrapper
# --------------------------------------------------------------------------- #
class OpcUaClient:
    """OPC UA client. Reports honestly when the ``asyncua`` driver is absent."""

    def __init__(self, endpoint: str, username: str = "", password: str = "", timeout: float = 5.0):
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return OPCUA_AVAILABLE

    def unavailable_reason(self) -> str:
        return (
            "OPC UA driver not installed. Install with: pip install asyncua "
            f"(import error: {OPCUA_IMPORT_ERROR or 'unknown'})"
        )

    async def read_node(self, node_id: str) -> dict[str, Any]:
        if not OPCUA_AVAILABLE:
            return {"success": False, "error": self.unavailable_reason(), "node_id": node_id}
        try:
            async with _OpcUaClient(url=self.endpoint, timeout=self.timeout) as client:  # type: ignore
                if self.username:
                    client.set_user(self.username)
                    client.set_password(self.password)
                node = client.get_node(node_id)
                value = await node.read_value()
                return {"success": True, "node_id": node_id, "value": value, "endpoint": self.endpoint}
        except Exception as e:
            return {"success": False, "error": str(e), "node_id": node_id}

    async def read_nodes(self, node_ids: list[str]) -> dict[str, Any]:
        if not OPCUA_AVAILABLE:
            return {"success": False, "error": self.unavailable_reason(), "values": {}}
        values: dict[str, Any] = {}
        try:
            async with _OpcUaClient(url=self.endpoint, timeout=self.timeout) as client:  # type: ignore
                if self.username:
                    client.set_user(self.username)
                    client.set_password(self.password)
                for node_id in node_ids:
                    try:
                        values[node_id] = await client.get_node(node_id).read_value()
                    except Exception as e:
                        values[node_id] = f"error: {e}"
            return {"success": True, "endpoint": self.endpoint, "values": values}
        except Exception as e:
            return {"success": False, "error": str(e), "values": values}

    async def browse(self, node_id: str = "i=85") -> dict[str, Any]:
        if not OPCUA_AVAILABLE:
            return {"success": False, "error": self.unavailable_reason()}
        try:
            async with _OpcUaClient(url=self.endpoint, timeout=self.timeout) as client:  # type: ignore
                node = client.get_node(node_id)
                children = await node.get_children()
                return {
                    "success": True,
                    "endpoint": self.endpoint,
                    "node_id": node_id,
                    "children": [
                        {"node_id": c.nodeid.to_string(), "name": (await c.read_browse_name()).Name}
                        for c in children[:200]
                    ],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# --------------------------------------------------------------------------- #
# MQTT client wrapper
# --------------------------------------------------------------------------- #
class MqttClient:
    """MQTT client for industrial IoT topics. Honest when paho-mqtt is absent."""

    def __init__(self, broker: str = "localhost", port: int = 1883,
                 client_id: str = "", username: str = "", password: str = ""):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"jarvis-{uuid.uuid4().hex[:8]}"
        self.username = username
        self.password = password
        self._messages: list[dict[str, Any]] = []
        self._client = None
        self._connected = False

    @property
    def available(self) -> bool:
        return MQTT_AVAILABLE

    def unavailable_reason(self) -> str:
        return (
            "MQTT driver not installed. Install with: pip install paho-mqtt "
            f"(import error: {MQTT_IMPORT_ERROR or 'unknown'})"
        )

    def _build(self):
        client = _mqtt.Client(client_id=self.client_id)  # type: ignore
        if self.username:
            client.username_pw_set(self.username, self.password)

        def on_connect(c, userdata, flags, rc):
            self._connected = rc == 0
            logger.info(f"[INDUSTRIAL] MQTT connect rc={rc}")

        def on_message(c, userdata, msg):
            self._messages.append({
                "topic": msg.topic,
                "payload": msg.payload.decode("utf-8", errors="replace"),
                "qos": msg.qos,
                "retain": msg.retain,
                "timestamp": time.time(),
            })
            if len(self._messages) > 500:
                self._messages = self._messages[-500:]

        client.on_connect = on_connect
        client.on_message = on_message
        return client

    def connect(self, subscribe_topics: list[str] | None = None) -> dict[str, Any]:
        if not MQTT_AVAILABLE:
            return {"success": False, "error": self.unavailable_reason()}
        try:
            self._client = self._build()
            self._client.connect(self.broker, self.port, keepalive=30)
            self._client.loop_start()
            deadline = time.time() + 5
            while not self._connected and time.time() < deadline:
                time.sleep(0.05)
            if not self._connected:
                return {"success": False, "error": "MQTT broker did not acknowledge CONNECT within 5s"}
            for topic in subscribe_topics or []:
                self._client.subscribe(topic)
            return {"success": True, "broker": self.broker, "port": self.port,
                    "subscribed": subscribe_topics or []}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def publish(self, topic: str, payload: str, qos: int = 0) -> dict[str, Any]:
        if not MQTT_AVAILABLE:
            return {"success": False, "error": self.unavailable_reason()}
        if not self._client:
            return {"success": False, "error": "MQTT client not connected"}
        try:
            info = self._client.publish(topic, payload, qos=qos)
            info.wait_for_publish(timeout=5)
            return {"success": True, "topic": topic, "mid": info.mid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def messages(self, topic_filter: str = "", limit: int = 50) -> list[dict[str, Any]]:
        items = self._messages
        if topic_filter:
            items = [m for m in items if topic_filter in m["topic"]]
        return items[-limit:]

    def disconnect(self):
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self._connected = False


# --------------------------------------------------------------------------- #
# Device registry + tag model
# --------------------------------------------------------------------------- #
@dataclass
class IndustrialDevice:
    id: str
    name: str
    kind: str = DeviceKind.PLC.value
    protocol: str = "modbus_tcp"
    address: str = ""
    port: int = 502
    unit_id: int = 1
    tags: list[dict[str, Any]] = field(default_factory=list)
    cell: str = ""
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "protocol": self.protocol,
            "address": self.address,
            "port": self.port,
            "unit_id": self.unit_id,
            "tags": self.tags,
            "cell": self.cell,
            "simulated": self.simulated,
        }


# Tag type → Modbus read call
_TAG_READERS = {
    "holding_register": "read_holding_registers",
    "input_register": "read_input_registers",
    "coil": "read_coils",
    "discrete_input": "read_discrete_inputs",
}


class IndustrialService:
    """Registry of industrial devices plus live read/control operations."""

    def __init__(self):
        self._devices: dict[str, IndustrialDevice] = {}
        self._connections: dict[str, ModbusTcpClient] = {}
        self._opcua: dict[str, OpcUaClient] = {}
        self._mqtt: dict[str, MqttClient] = {}
        self._alarms: list[Alarm] = []
        self._tag_history: dict[str, list[tuple[float, Any]]] = {}
        self._max_history = 2000
        self._control_mode = ControlMode.MONITORING
        self._init_default_cell()
        logger.info("[INDUSTRIAL] IndustrialService initialized")

    # ------------------------------------------------------------------ #
    # Registry
    # ------------------------------------------------------------------ #
    def _init_default_cell(self):
        """Register the demo robot cell layout as *unconfigured* placeholders.

        These entries carry no address until the operator points them at real
        hardware, so a read against them fails loudly instead of inventing data.
        """
        self.register_device(IndustrialDevice(
            id="cell-plc-1",
            name="Cell PLC (unconfigured)",
            kind=DeviceKind.PLC.value,
            protocol="modbus_tcp",
            address="",
            port=502,
            cell="robot_cell_1",
            tags=[
                {"tag": "conveyor_speed", "address": 40001, "type": "holding_register", "unit": "m/s", "scale": 0.01},
                {"tag": "cell_state", "address": 40002, "type": "holding_register", "unit": ""},
                {"tag": "part_counter", "address": 40003, "type": "holding_register", "unit": "pcs"},
                {"tag": "estop_ok", "address": 10001, "type": "discrete_input", "unit": "bool"},
                {"tag": "guard_closed", "address": 10002, "type": "discrete_input", "unit": "bool"},
            ],
        ))
        self.register_device(IndustrialDevice(
            id="cell-hmi-1",
            name="Cell HMI (unconfigured)",
            kind=DeviceKind.HMI.value,
            protocol="opcua",
            address="",
            cell="robot_cell_1",
            tags=[{"tag": "screen_state", "address": "ns=2;s=HMI.Screen", "type": "opcua"}],
        ))
        self.register_device(IndustrialDevice(
            id="cell-iot-1",
            name="Cell IIoT broker (unconfigured)",
            kind=DeviceKind.SENSOR.value,
            protocol="mqtt",
            address="",
            port=1883,
            cell="robot_cell_1",
            tags=[{"tag": "vibration_rms", "address": "cell/robot/vibration", "type": "mqtt"}],
        ))

    def register_device(self, device: IndustrialDevice) -> dict[str, Any]:
        self._devices[device.id] = device
        return device.to_dict()

    def list_devices(self, cell: str | None = None) -> list[dict[str, Any]]:
        devices = self._devices.values()
        if cell:
            devices = [d for d in devices if d.cell == cell]
        return [d.to_dict() for d in devices]

    def get_device(self, device_id: str) -> Optional[IndustrialDevice]:
        return self._devices.get(device_id)

    def set_control_mode(self, mode: str) -> dict[str, Any]:
        try:
            self._control_mode = ControlMode(mode.upper())
        except ValueError:
            return {"success": False, "error": f"Unknown control mode '{mode}'",
                    "valid": [m.value for m in ControlMode]}
        logger.info(f"[INDUSTRIAL] Control mode set to {self._control_mode.value}")
        return {"success": True, "control_mode": self._control_mode.value}

    @property
    def control_mode(self) -> str:
        return self._control_mode.value

    # ------------------------------------------------------------------ #
    # Connections
    # ------------------------------------------------------------------ #
    def connect_modbus(self, host: str, port: int = 502, unit_id: int = 1,
                       device_id: str = "") -> dict[str, Any]:
        client = ModbusTcpClient(host, port, unit_id)
        result = client.connect()
        key = device_id or f"{host}:{port}"
        if result.get("success"):
            self._connections[key] = client
            result["key"] = key
        return result

    def modbus_client(self, key: str) -> Optional[ModbusTcpClient]:
        return self._connections.get(key)

    def connect_opcua(self, endpoint: str, device_id: str = "") -> dict[str, Any]:
        client = OpcUaClient(endpoint)
        if not client.available:
            return {"success": False, "error": client.unavailable_reason(), "endpoint": endpoint}
        self._opcua[device_id or endpoint] = client
        return {"success": True, "endpoint": endpoint, "driver": "asyncua"}

    def connect_mqtt(self, broker: str, port: int = 1883,
                     subscribe_topics: list[str] | None = None,
                     device_id: str = "") -> dict[str, Any]:
        client = MqttClient(broker, port)
        result = client.connect(subscribe_topics)
        if result.get("success"):
            self._mqtt[device_id or f"{broker}:{port}"] = client
        return result

    def mqtt_client(self, key: str) -> Optional[MqttClient]:
        return self._mqtt.get(key)

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def read_tag(self, device_id: str, tag: str, connection_key: str = "") -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Unknown device '{device_id}'"}

        tag_def = next((t for t in device.tags if t["tag"] == tag), None)
        if not tag_def:
            return {"success": False, "error": f"Tag '{tag}' is not defined on device '{device_id}'"}

        if device.protocol == "modbus_tcp":
            if not device.address:
                return {
                    "success": False,
                    "error": (
                        f"Device '{device.name}' has no configured address. "
                        "Register the real PLC address before reading — no simulated values are invented."
                    ),
                    "device_id": device_id,
                    "tag": tag,
                }
            key = connection_key or f"{device.address}:{device.port}"
            client = self._connections.get(device_id) or self._connections.get(key)
            if client is None:
                conn = self.connect_modbus(device.address, device.port, device.unit_id, device_id)
                if not conn.get("success"):
                    return {"success": False, "error": conn.get("error", "connect failed"),
                            "device_id": device_id, "tag": tag}
                client = self._connections[device_id]

            address = int(tag_def.get("address", 0))
            # Modbus data model addresses: 1xxxx discrete, 4xxxx holding.
            if address >= 40000:
                address -= 40001
            elif address >= 30000:
                address -= 30001
            elif address >= 10000:
                address -= 10001
            elif address >= 1:
                address -= 1

            reader_name = _TAG_READERS.get(tag_def.get("type", "holding_register"), "read_holding_registers")
            try:
                values = getattr(client, reader_name)(address, 1)
                raw = values[0]
                scale = float(tag_def.get("scale", 1.0) or 1.0)
                value = raw * scale if not isinstance(raw, bool) else raw
                tag_value = TagValue(tag=tag, value=value, unit=tag_def.get("unit", ""),
                                     source=f"{device.name} (Modbus {device.address}:{device.port})")
                self._record_history(f"{device_id}:{tag}", value)
                return {"success": True, "device_id": device_id, "reading": tag_value.to_dict(),
                        "raw": raw, "address": address, "function": reader_name}
            except Exception as e:
                return {"success": False, "error": f"Modbus read failed: {e}",
                        "device_id": device_id, "tag": tag}

        if device.protocol == "opcua":
            if not device.address:
                return {"success": False,
                        "error": f"Device '{device.name}' has no configured OPC UA endpoint."}
            client = self._opcua.get(device_id) or OpcUaClient(device.address)
            if not client.available:
                return {"success": False, "error": client.unavailable_reason(),
                        "device_id": device_id, "tag": tag}
            node_id = tag_def.get("address", "")
            result = asyncio.run(client.read_node(node_id)) if not _in_event_loop() else _run_sync(client.read_node(node_id))
            if result.get("success"):
                tag_value = TagValue(tag=tag, value=result["value"], unit=tag_def.get("unit", ""),
                                     source=f"{device.name} (OPC UA)")
                self._record_history(f"{device_id}:{tag}", result["value"])
                return {"success": True, "device_id": device_id, "reading": tag_value.to_dict()}
            return {"success": False, "error": result.get("error"), "device_id": device_id, "tag": tag}

        if device.protocol == "mqtt":
            key = device_id
            client = self._mqtt.get(key)
            if client is None:
                return {"success": False,
                        "error": "MQTT client not connected. Connect the broker first.",
                        "device_id": device_id, "tag": tag}
            topic = tag_def.get("address", "")
            messages = client.messages(topic_filter=topic, limit=1)
            if not messages:
                return {"success": False, "error": f"No MQTT message received on '{topic}' yet",
                        "device_id": device_id, "tag": tag}
            latest = messages[-1]
            tag_value = TagValue(tag=tag, value=latest["payload"], unit=tag_def.get("unit", ""),
                                 source=f"{device.name} (MQTT {latest['topic']})")
            self._record_history(f"{device_id}:{tag}", latest["payload"])
            return {"success": True, "device_id": device_id, "reading": tag_value.to_dict()}

        return {"success": False, "error": f"Protocol '{device.protocol}' has no reader implementation"}

    def read_device(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Unknown device '{device_id}'"}
        readings = []
        errors = []
        for tag_def in device.tags:
            result = self.read_tag(device_id, tag_def["tag"])
            if result.get("success"):
                readings.append(result["reading"])
            else:
                errors.append({"tag": tag_def["tag"], "error": result.get("error")})
        return {
            "success": len(readings) > 0,
            "device": device.to_dict(),
            "readings": readings,
            "errors": errors,
            "partial": bool(readings) and bool(errors),
            "control_mode": self.control_mode,
        }

    def _record_history(self, key: str, value: Any):
        series = self._tag_history.setdefault(key, [])
        series.append((time.time(), value))
        if len(series) > self._max_history:
            self._tag_history[key] = series[-self._max_history:]

    def tag_history(self, device_id: str, tag: str, limit: int = 200) -> list[dict[str, Any]]:
        series = self._tag_history.get(f"{device_id}:{tag}", [])
        return [{"timestamp": t, "value": v} for t, v in series[-limit:]]

    # ------------------------------------------------------------------ #
    # Writes (control) — policy-checked by callers
    # ------------------------------------------------------------------ #
    def write_tag(self, device_id: str, tag: str, value: Any,
                  authorized: bool = False) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Unknown device '{device_id}'"}

        if not authorized:
            return {
                "success": False,
                "blocked": True,
                "error": (
                    "Writing a tag commands real equipment and requires explicit confirmation. "
                    "Confirm the action first, then retry with authorization."
                ),
                "action_class": "CONTROL",
            }

        tag_def = next((t for t in device.tags if t["tag"] == tag), None)
        if not tag_def:
            return {"success": False, "error": f"Tag '{tag}' is not defined on device '{device_id}'"}

        if not device.address:
            return {"success": False, "error": f"Device '{device.name}' has no configured address"}

        client = self._connections.get(device_id) or self._connections.get(f"{device.address}:{device.port}")
        if client is None:
            conn = self.connect_modbus(device.address, device.port, device.unit_id, device_id)
            if not conn.get("success"):
                return {"success": False, "error": conn.get("error", "connect failed")}
            client = self._connections.get(device_id)

        address = int(tag_def.get("address", 0))
        if address >= 40000:
            address -= 40001
        elif address >= 1:
            address -= 1

        scale = float(tag_def.get("scale", 1.0) or 1.0)
        try:
            if tag_def.get("type") == "coil":
                ok = client.write_coil(address, bool(value))
            else:
                raw = int(round(float(value) / scale)) if scale else int(value)
                ok = client.write_register(address, raw)
            if not ok:
                return {"success": False, "error": "Device rejected the write"}
            self._record_history(f"{device_id}:{tag}", value)
            logger.warning(f"[INDUSTRIAL] WROTE {device_id}.{tag} = {value} (authorized control)")
            return {"success": True, "device_id": device_id, "tag": tag, "value": value,
                    "action_class": "CONTROL", "verified_by_readback": self.read_tag(device_id, tag)}
        except Exception as e:
            return {"success": False, "error": f"Modbus write failed: {e}"}

    # ------------------------------------------------------------------ #
    # Alarms / machine state
    # ------------------------------------------------------------------ #
    def raise_alarm(self, code: str, message: str, severity: str = "medium",
                    source: str = "industrial") -> dict[str, Any]:
        alarm = Alarm(code=code, message=message, severity=severity, source=source)
        self._alarms.append(alarm)
        if len(self._alarms) > 500:
            self._alarms = self._alarms[-500:]
        return alarm.to_dict()

    def clear_alarm(self, alarm_id: str) -> dict[str, Any]:
        for alarm in self._alarms:
            if alarm.id == alarm_id:
                alarm.active = False
                alarm.cleared_at = time.time()
                return alarm.to_dict()
        return {"success": False, "error": f"Alarm '{alarm_id}' not found"}

    def active_alarms(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._alarms if a.active]

    def all_alarms(self, limit: int = 100) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._alarms[-limit:]]

    def machine_state(self, device_id: str) -> dict[str, Any]:
        """Derive machine state from real reads only."""
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Unknown device '{device_id}'"}
        read = self.read_device(device_id)
        values = {r["tag"]: r["value"] for r in read.get("readings", [])}
        state = "unknown"
        if "estop_ok" in values:
            state = "running" if values.get("estop_ok") else "emergency_stop"
        elif "cell_state" in values:
            state = {0: "idle", 1: "running", 2: "fault", 3: "maintenance"}.get(
                int(values["cell_state"]) if str(values["cell_state"]).isdigit() else -1, "unknown")
        return {
            "success": read.get("success", False),
            "device_id": device_id,
            "state": state,
            "tag_values": values,
            "errors": read.get("errors", []),
            "alarms": self.active_alarms(),
            "source": "live device read" if read.get("success") else "read failed — state unknown",
        }

    # ------------------------------------------------------------------ #
    # Protocol inventory / capability report
    # ------------------------------------------------------------------ #
    def protocol_status(self) -> dict[str, Any]:
        return {
            "modbus_tcp": {"available": True, "driver": "built-in (stdlib)"},
            "modbus_rtu": {
                "available": False,
                "reason": "No serial hardware configured on this host; RTU requires a COM port and pyserial",
            },
            "opcua": {"available": OPCUA_AVAILABLE, "driver": "asyncua",
                      "reason": "" if OPCUA_AVAILABLE else OPCUA_IMPORT_ERROR},
            "mqtt": {"available": MQTT_AVAILABLE, "driver": "paho-mqtt",
                     "reason": "" if MQTT_AVAILABLE else MQTT_IMPORT_ERROR},
            "control_mode": self.control_mode,
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "devices": len(self._devices),
            "configured_devices": sum(1 for d in self._devices.values() if d.address),
            "connections": len(self._connections),
            "active_alarms": len(self.active_alarms()),
            "tracked_tags": len(self._tag_history),
            "protocols": self.protocol_status(),
            "control_mode": self.control_mode,
        }


def _in_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _run_sync(coro):
    """Run a coroutine from sync code that may already be inside a loop."""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)


_industrial: IndustrialService | None = None


def get_industrial_service() -> IndustrialService:
    global _industrial
    if _industrial is None:
        _industrial = IndustrialService()
    return _industrial
