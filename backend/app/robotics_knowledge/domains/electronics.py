"""Electronics — knowledge domain for robotics electronics and circuits."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_electronics_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="electronics",
        description="Robotics electronics — circuits, power supplies, microcontrollers, PCB design, and signal conditioning for robot systems.",
        subcategories=["basics", "power", "microcontrollers", "pcb", "interfacing", "troubleshooting"],
    )

    domain.add_entry(KnowledgeEntry(
        id="elec-basics-001",
        title="Electronics Fundamentals for Robotics",
        content="""Basic electronics knowledge is essential for robotics — understanding voltage, current, resistance, and common components.

Ohm's Law:
- V = I × R (Voltage = Current × Resistance)
- I = V / R (Current = Voltage / Resistance)
- R = V / I (Resistance = Voltage / Current)

Power:
- P = V × I (Power = Voltage × Current)
- Units: Watts (W), milliwatts (mW)
- Example: 12V motor drawing 2A → P = 24W

Common Components:

1. Resistors
   - Limit current, divide voltage
   - Values: 1Ω to 10MΩ, power rating 1/8W to 5W
   - Color code: 4-band (brown-black-red = 1kΩ ±2%)
   - Use: Pull-up/pull-down, current limiting, voltage divider

2. Capacitors
   - Store energy, filter noise, couple AC signals
   - Types: Ceramic (1pF-1μF), electrolytic (1μF-10000μF), tantalum
   - Voltage rating: Must exceed circuit voltage
   - Use: Decoupling (100nF near IC), filtering, timing circuits

3. Diodes
   - Allow current in one direction only
   - Types: Rectifier (1N4007), Schottky (1N5819, low voltage drop), Zener (voltage reference)
   - Use: Reverse polarity protection, flyback (motor suppression), voltage regulation

4. Transistors
   - BJT (NPN/PNP): Current amplifier, switch
   - MOSFET (N-channel/P-channel): Voltage-controlled switch, low Rds(on)
   - Use: Switching loads (motors, relays, LEDs), amplification

5. LEDs
   - Light-emitting diodes (indicator, illumination)
   - Forward voltage: 2V (red) to 3.3V (blue/white)
   - Current: 10-20mA typical, use current-limiting resistor
   - Resistor: R = (Vsupply - Vled) / Iled = (5V - 2V) / 20mA = 150Ω""",
        domain="electronics",
        category="basics",
        tags=["electronics", "basics", "ohm's law", "components", "resistors", "capacitors"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "LED resistor: 5V supply, 2V LED, 20mA → R = (5-2)/0.02 = 150Ω",
            "Voltage divider: Vout = Vin × R2/(R1+R2) → 5V to 3.3V with 1kΩ and 2kΩ",
            "Decoupling: 100nF ceramic capacitor near every IC power pin",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="elec-power-001",
        title="Power Supplies and Battery Systems",
        content="""Power systems provide stable voltage and sufficient current for all robot subsystems — motors, controllers, sensors, and communication.

Power Supply Types:

1. AC-DC Power Supplies (Mains Powered)
   - Input: 110-240V AC (50/60Hz)
   - Output: 5V, 12V, 24V, 48V DC
   - Power: 10W to 10kW
   - Types: Linear (heavy, low noise), switching (light, efficient, noisy)
   - Use: Bench robots, industrial systems (always plugged in)

2. Battery Systems (Mobile Robots)
   - LiPo (Lithium Polymer): 3.7V/cell, high energy density, requires protection
     - 2S = 7.4V, 3S = 11.1V, 4S = 14.8V
     - Discharge rate: C rating (1C = capacity in Ah, e.g., 5000mAh at 1C = 5A)
   - Li-ion (Lithium Ion): 3.6V/cell, more stable, lower discharge rate
   - NiMH (Nickel Metal Hydride): 1.2V/cell, safe, lower energy density
   - Lead-acid: 2V/cell, heavy, cheap, high current (starter batteries)

Battery Management:
- BMS (Battery Management System): Cell balancing, overcharge/overdischarge protection
- Voltage monitoring: ADC measurement, low-battery alarm
- Current monitoring: Shunt resistor or Hall effect sensor
- Temperature monitoring: Prevent thermal runaway (LiPo)
- Capacity calculation: Coulomb counting (integrate current over time)

Power Distribution:
- Main battery → DC-DC converters → subsystem voltages
- Buck converter: Step down voltage (12V → 5V, 90-95% efficient)
- Boost converter: Step up voltage (3.7V → 5V, 85-90% efficient)
- LDO regulator: Low dropout linear (5V → 3.3V, inefficient but low noise)

Safety:
- Fuse: Overcurrent protection (fast-blow for motors, slow-blow for electronics)
- Emergency stop: Cut power to motors, keep control electronics alive
- Reverse polarity protection: Diode or MOSFET (prevents damage from wrong battery connection)
- Isolation: Separate motor power from logic power (reduce noise)""",
        domain="electronics",
        category="power",
        tags=["electronics", "power", "battery", "supply", "voltage", "current"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["elec-basics-001"],
        examples=[
            "LiPo 4S 5000mAh: 14.8V nominal, 5A continuous (1C), 60A peak (12C)",
            "Buck converter: 12V input → 5V/3A output for Raspberry Pi",
            "Fuse: 10A fast-blow on motor supply, 2A slow-blow on electronics",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="elec-microcontrollers-001",
        title="Microcontrollers for Robotics",
        content="""Microcontrollers (MCUs) are embedded computers on a single chip — used for low-level control, sensor reading, and actuator control in robots.

Popular Robotics MCUs:

1. Arduino (ATmega328P)
   - CPU: 16MHz AVR, 32KB flash, 2KB SRAM
   - I/O: 14 digital (6 PWM), 6 analog (10-bit ADC)
   - Communication: UART, SPI, I2C
   - Use: Learning, simple robots, sensor nodes
   - Pros: Huge community, easy to use, shield ecosystem
   - Cons: Limited performance, 5V logic

2. ESP32
   - CPU: 240MHz dual-core Xtensa, 4MB flash, 520KB SRAM
   - Wireless: WiFi 802.11 b/g/n, Bluetooth 4.2 + BLE
   - I/O: 34 GPIO, 12-bit ADC, DAC, PWM
   - Use: IoT robots, wireless sensor networks, mobile robots
   - Pros: WiFi/BLE, low cost ($3), low power
   - Cons: Arduino-compatible but more complex

3. STM32 (ARM Cortex-M)
   - CPU: 72-480MHz ARM Cortex-M0/M3/M4/M7
   - Variants: STM32F1 (basic), STM32F4 (DSP, FPU), STM32H7 (high-performance)
   - I/O: Rich peripherals (UART, SPI, I2C, CAN, USB, Ethernet)
   - Use: Industrial robots, drones, high-performance control
   - Pros: High performance, low cost, wide range
   - Cons: Steeper learning curve, requires STM32CubeIDE

4. Teensy 4.1
   - CPU: 600MHz ARM Cortex-M7, 8MB flash, 1MB SRAM
   - I/O: 40 digital, 18 analog (12-bit ADC), USB
   - Use: Audio processing, fast control, data logging
   - Pros: Very fast, Arduino-compatible, USB native
   - Cons: More expensive ($30)

5. Raspberry Pi Pico (RP2040)
   - CPU: 133MHz dual-core ARM Cortex-M0+
   - I/O: 26 GPIO, 3 analog (12-bit ADC), PIO (programmable I/O)
   - Use: Custom peripherals, fast I/O, education
   - Pros: Low cost ($4), MicroPython support, PIO for custom protocols
   - Cons: No wireless (use Pico W for WiFi)

Selection Criteria:
- Performance: Clock speed, flash, SRAM
- Peripherals: UART, SPI, I2C, ADC, PWM, CAN, USB
- Power consumption: Battery-operated vs plugged in
- Ecosystem: Libraries, community, development tools
- Cost: $1 (basic) to $50 (high-performance)""",
        domain="electronics",
        category="microcontrollers",
        tags=["electronics", "microcontroller", "arduino", "esp32", "stm32"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["elec-basics-001"],
        examples=[
            "Arduino Uno: 16MHz, 32KB flash, 14 I/O — simple robot arm",
            "ESP32: 240MHz dual-core, WiFi/BLE — mobile robot with remote control",
            "STM32F4: 168MHz, FPU, CAN — drone flight controller",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="elec-pcb-001",
        title="PCB Design for Robotics",
        content="""PCB (Printed Circuit Board) design integrates electronics into a compact, reliable form factor — essential for production robots and custom controllers.

PCB Design Workflow:
1. Schematic capture: Draw circuit with symbols (KiCad, Altium, Eagle)
2. Component selection: Choose packages (0805, SOT-23, QFP-48)
3. PCB layout: Place components, route traces
4. Design rule check (DRC): Verify clearances, trace widths
5. Gerber generation: Manufacturing files (copper, solder mask, silkscreen)
6. Order PCB: JLCPCB, PCBWay, Seeed Studio (2-5 day turnaround)

PCB Layers:
- Top copper: Components, traces
- Bottom copper: Ground plane, additional traces
- Top silkscreen: Component labels, reference designators
- Solder mask: Green (typically), prevents solder bridges

Design Guidelines:
- Trace width: Current capacity (1oz copper, 10°C rise):
  - 0.5A → 10mil (0.25mm)
  - 1A → 20mil (0.5mm)
  - 3A → 60mil (1.5mm)
  - 10A → 200mil (5mm) or use thicker copper (2oz)
- Clearances: Minimum 6mil (0.15mm) for most PCB houses
- Decoupling: 100nF capacitor near every IC power pin (<5mm)
- Ground plane: Continuous ground on layer 2 (reduces noise, EMI)
- Thermal relief: Connect power pads with thin traces (easier soldering)

Common Robotics PCBs:
- Motor driver: H-bridge, current sensing, PWM input
- Sensor interface: Signal conditioning, ADC, communication (I2C/SPI)
- Power distribution: Battery input, voltage regulation, fuses, connectors
- Breakout board: Convert pitch (2.54mm → 1.27mm), level shifting (5V → 3.3V)

Manufacturing:
- 2-layer PCB: $5-20 for 5 boards (100x100mm)
- 4-layer PCB: $20-50 (better for high-speed, noise-sensitive)
- Assembly: Hand solder or PCBA service (JLCPCB, PCBWay)
- Testing: Continuity check, power-on test, functional test""",
        domain="electronics",
        category="pcb",
        tags=["electronics", "pcb", "design", "layout", "manufacturing"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["elec-basics-001", "elec-microcontrollers-001"],
        examples=[
            "Motor driver PCB: L298N H-bridge, current sense resistor, screw terminals",
            "Trace width: 1oz copper, 1A → 20mil (0.5mm) trace width",
            "Decoupling: 100nF 0805 capacitor within 5mm of every IC VCC pin",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="elec-troubleshoot-001",
        title="Electronics Troubleshooting for Robotics",
        content="""Common electronics problems in robotics and systematic troubleshooting approaches.

Troubleshooting Tools:
- Multimeter: Voltage, current, resistance, continuity
- Oscilloscope: Waveform visualization (UART, PWM, noise)
- Logic analyzer: Digital signal decoding (I2C, SPI, UART)
- Thermal camera: Find hot components (overheating, shorts)
- Power supply: Adjustable voltage/current with current limiting

Common Problems and Fixes:

1. No power / dead board
   - Check: Power supply voltage, fuse, reverse polarity protection
   - Measure: Voltage at power input, after regulator, at IC VCC pins
   - Fix: Replace fuse, check for shorts (measure resistance VCC to GND)

2. Microcontroller not programming
   - Check: Power (3.3V/5V), ground, reset pin, programming connections
   - Measure: Voltage on reset pin (should be high), crystal oscillation (oscilloscope)
   - Fix: Check bootloader, try slower programming speed, verify pinout

3. Noisy sensor readings
   - Check: Grounding, shielding, power supply ripple
   - Measure: Oscilloscope on sensor output, power supply ripple
   - Fix: Add decoupling capacitors, use shielded cables, separate analog/digital ground

4. Motor causes system reset
   - Check: Power supply capacity, ground loops, EMI
   - Measure: Voltage drop during motor start (oscilloscope)
   - Fix: Separate motor/logic power, add bulk capacitor, use opto-isolators

5. Communication not working (I2C/SPI/UART)
   - Check: Wiring (TX→RX, RX→TX), baud rate, pull-up resistors (I2C)
   - Measure: Oscilloscope on SDA/SCL (I2C), MOSI/MISO/SCK (SPI)
   - Fix: Verify address (I2C scanner), check bit order, add pull-ups (4.7kΩ for I2C)

6. Intermittent failures
   - Check: Loose connections, vibration, temperature
   - Measure: Monitor during failure (oscilloscope, data logger)
   - Fix: Re-solder joints, add strain relief, conformal coating for moisture

7. Overheating components
   - Check: Current draw, load, ventilation
   - Measure: Thermal camera or thermocouple on hot component
   - Fix: Add heatsink, reduce load, check for shorts, improve airflow""",
        domain="electronics",
        category="troubleshooting",
        tags=["electronics", "troubleshooting", "debugging", "multimeter", "oscilloscope"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["elec-basics-001"],
        examples=[
            "No power: Check fuse with multimeter continuity, measure voltage at power input",
            "Noisy ADC: Add 100nF decoupling cap, use shielded cable, separate analog ground",
            "I2C not working: Run I2C scanner, check pull-ups (4.7kΩ to 3.3V), verify address",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Electronics domain with {len(domain.entries)} entries")
    return domain
