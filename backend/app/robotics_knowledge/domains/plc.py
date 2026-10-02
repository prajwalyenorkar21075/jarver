"""PLC Programming — knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_plc_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="plc",
        description="PLC (Programmable Logic Controller) programming — ladder logic, structured text, function blocks, and industrial automation control.",
        subcategories=["basics", "ladder", "structured_text", "function_blocks", "tags", "communication", "troubleshooting"],
    )

    domain.add_entry(KnowledgeEntry(
        id="plc-basics-001",
        title="PLC Basics and Architecture",
        content="""PLCs are industrial computers designed for real-time control in harsh environments — used in manufacturing, process control, and automation.

PLC Architecture:
- CPU: Executes program logic, handles communication
- I/O Modules: Digital (on/off) and Analog (0-10V, 4-20mA)
- Power Supply: 24VDC typical for industrial control
- Memory: Program memory, data memory, retentive memory

PLC Programming Languages (IEC 61131-3):
1. Ladder Logic (LD) — Graphical, relay-based, most common in North America
2. Function Block Diagram (FBD) — Graphical blocks connected by wires
3. Structured Text (ST) — High-level text language (similar to Pascal/C)
4. Instruction List (IL) — Low-level assembly-like (rarely used now)
5. Sequential Function Chart (SFC) — State machine / step-based

Scan Cycle:
1. Read inputs (physical → memory)
2. Execute program (top to bottom, left to right)
3. Write outputs (memory → physical)
4. Housekeeping (communication, diagnostics)

Typical scan time: 1-10ms for most industrial applications""",
        domain="plc",
        category="basics",
        tags=["plc", "basics", "architecture", "iec 61131"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Allen-Bradley (Rockwell) — Studio 5000, Logix5000",
            "Siemens — TIA Portal, S7-1200/1500",
            "Mitsubishi — GX Works2/3, MELSEC iQ-R",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-ladder-001",
        title="Ladder Logic Programming",
        content="""Ladder Logic is the most common PLC programming language — uses graphical rungs resembling electrical relay circuits.

Basic Instructions:
- XIC (Examine If Closed) — Normally open contact: |--[ ]--|
- XIO (Examine If Open) — Normally closed contact: |--[/]--|
- OTE (Output Energize) — Coil: --( )--
- OTL (Output Latch) — Latch coil: --(L)--
- OTU (Output Unlatch) — Unlatch coil: --(U)--

Timer Instructions:
- TON (Timer On Delay) — Delay before output turns ON
- TOF (Timer Off Delay) — Delay before output turns OFF
- RTO (Retentive Timer On) — Accumulates time across power cycles

Counter Instructions:
- CTU (Count Up) — Counts rising edges, increments accumulator
- CTD (Count Down) — Counts down from preset
- CTUD (Count Up/Down) — Bidirectional counter

Compare Instructions:
- EQU (Equal), NEQ (Not Equal)
- GRT (Greater Than), LES (Less Than)
- GEQ (Greater/Equal), LEQ (Less/Equal)

Move Instructions:
- MOV (Move) — Copy value to tag
- MVM (Masked Move) — Move with bit masking""",
        domain="plc",
        category="ladder",
        tags=["plc", "ladder logic", "contacts", "coils", "timers"],
        difficulty=DifficultyLevel.BEGINNER,
        prerequisites=["plc-basics-001"],
        examples=[
            "Start/Stop circuit: XIC(Start) + XIC(Stop_NC) → OTE(Motor)",
            "Timer: TON(In:=Sensor, PT:=T#5s) → Q activates after 5 seconds",
            "Counter: CTU(PartSensor, PV:=10) → Done when 10 parts counted",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-structured-text-001",
        title="Structured Text (ST) Programming",
        content="""Structured Text is a high-level PLC language similar to Pascal — used for complex algorithms, math, and data processing.

Basic syntax:
```
// Variable declaration
VAR
    counter : INT := 0;
    temperature : REAL;
    running : BOOL := FALSE;
END_VAR

// IF/THEN/ELSE
IF temperature > 100.0 THEN
    alarm := TRUE;
    heater := FALSE;
ELSIF temperature < 50.0 THEN
    heater := TRUE;
ELSE
    alarm := FALSE;
END_IF;

// FOR loop
FOR i := 0 TO 99 DO
    array[i] := i * 2;
END_FOR;

// WHILE loop
WHILE counter < 10 DO
    counter := counter + 1;
END_WHILE;

// CASE statement
CASE state OF
    0: // IDLE
        output := FALSE;
    1: // RUNNING
        output := TRUE;
    2: // ERROR
        output := FALSE;
        alarm := TRUE;
END_CASE;
```

Functions and Function Blocks:
- FUNCTION add(a: INT, b: INT) : INT — returns single value
- FUNCTION_BLOCK motor_ctrl — has inputs, outputs, internal state""",
        domain="plc",
        category="structured_text",
        tags=["plc", "structured text", "ST", "programming"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["plc-basics-001"],
        examples=[
            "PID control: output := Kp * error + Ki * integral + Kd * derivative;",
            "Array processing: FOR i := 0 TO 99 DO sum := sum + array[i]; END_FOR;",
            "State machine: CASE step OF 0: init(); 1: run(); 2: cleanup(); END_CASE;",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-function-blocks-001",
        title="Function Blocks — Reusable Control Modules",
        content="""Function Blocks (FBs) are reusable program units with internal memory — ideal for motors, valves, PID loops, and complex equipment.

Function Block structure:
```
FUNCTION_BLOCK Motor_Control
VAR_INPUT
    start_cmd : BOOL;
    stop_cmd : BOOL;
    overload : BOOL;
END_VAR

VAR_OUTPUT
    running : BOOL;
    faulted : BOOL;
END_VAR

VAR
    latched_fault : BOOL;
END_VAR

// Logic
IF stop_cmd OR overload THEN
    running := FALSE;
    IF overload THEN
        latched_fault := TRUE;
        faulted := TRUE;
    END_IF;
ELSIF start_cmd AND NOT latched_fault THEN
    running := TRUE;
END_IF;
```

Standard Function Blocks (IEC 61131-3):
- SR (Set-Reset bistable)
- RS (Reset-Set bistable)
- CTU, CTD, CTUD (Counters)
- TON, TOF, TP (Timers)
- PID_CTRL (PID control loop)

Using Function Blocks:
```
VAR
    motor1 : Motor_Control;
    motor2 : Motor_Control;
END_VAR

motor1(start_cmd := button1, stop_cmd := button2, overload := sensor1);
motor2(start_cmd := button3, stop_cmd := button4, overload := sensor2);

IF motor1.running THEN
    // Motor 1 is running
END_IF;
```""",
        domain="plc",
        category="function_blocks",
        tags=["plc", "function blocks", "reusable", "object-oriented"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["plc-structured-text-001"],
        examples=[
            "Motor control FB with start/stop/overload/fault",
            "Valve control FB with open/close/feedback/timeout",
            "PID loop FB with tuning parameters and auto-tune mode",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-tags-001",
        title="PLC Tags and Data Types",
        content="""Tags are named variables in PLC programs — represent physical I/O, internal calculations, and communication data.

Data Types:
- BOOL — TRUE/FALSE, 1 bit (digital inputs/outputs)
- INT — 16-bit integer (-32768 to 32767)
- DINT — 32-bit integer (-2B to 2B)
- REAL — 32-bit floating point (6-7 digits precision)
- LREAL — 64-bit floating point (15-16 digits precision)
- STRING — Text (fixed or variable length)
- TIME — Duration (T#1s, T#500ms, T#1h30m)
- DATE — Calendar date (D#2026-10-02)
- TOD — Time of day (TOD#14:30:00)
- ARRAY — Collection of same-type elements
- STRUCT — Collection of different-type elements

Tag Scopes:
- Local tags — Visible only in program/FB where defined
- Global tags — Visible across all programs (controller scope)
- I/O tags — Map to physical inputs/outputs
- Produced/Consumed tags — Shared between PLCs via network

Tag Naming Conventions:
- Use descriptive names: Motor1_Speed, Tank1_Level, Conveyor1_Running
- Prefix for type: b_MotorRunning (BOOL), i_Count (INT), r_Temperature (REAL)
- Hierarchy: Line1_Cell2_Robot3_Servo4_Enable""",
        domain="plc",
        category="tags",
        tags=["plc", "tags", "data types", "variables"],
        difficulty=DifficultyLevel.BEGINNER,
        prerequisites=["plc-basics-001"],
        examples=[
            "BOOL start_button := digital_input_0;",
            "REAL temperature := analog_input_1 * 100.0 / 32767.0;",
            "STRUCT RobotPos : x REAL, y REAL, z REAL, gripper BOOL;",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-communication-001",
        title="PLC Communication Protocols",
        content="""PLCs communicate with other devices using industrial protocols — each has specific use cases and characteristics.

Common Protocols:

1. EtherNet/IP (Ethernet Industrial Protocol)
   - Uses standard Ethernet, CIP messaging
   - Implicit (cyclic I/O) and Explicit (configuration) messaging
   - Common in Allen-Bradley/Rockwell systems

2. PROFINET
   - Siemens standard, based on Ethernet
   - RT (Real-Time) and IRT (Isochronous Real-Time)
   - Device replacement without PG/PC

3. Modbus TCP
   - Simple request/reply protocol
   - Master/slave architecture
   - Widely supported, easy to implement

4. OPC UA (Open Platform Communications Unified Architecture)
   - Platform-independent, secure
   - Client/server and publish/subscribe
   - Industry 4.0 standard, information modeling

5. EtherCAT
   - High-performance, deterministic
   - Process data in single Ethernet frame
   - Used in motion control applications

6. CANopen / DeviceNet
   - Fieldbus protocols for sensors/actuators
   - CAN-based, robust in noisy environments

Configuration:
- Assign IP addresses, subnet masks
- Configure I/O mapping (produced/consumed tags)
- Set communication rates and timeouts
- Test with diagnostic tools (ping, protocol analyzers)""",
        domain="plc",
        category="communication",
        tags=["plc", "communication", "ethernet", "protocols", "modbus", "profinet"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["plc-basics-001"],
        examples=[
            "EtherNet/IP: Add device in Studio 5000, configure connection parameters",
            "Modbus TCP: Use MB_MASTER/MB_SLAVE function blocks",
            "OPC UA: Configure server endpoints, security certificates, node subscriptions",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="plc-troubleshoot-001",
        title="Common PLC Programming Errors and Fixes",
        content="""Frequent PLC programming errors and their solutions:

1. Output not turning on
   Fix: Check all interlocks (safety, permissives), verify I/O mapping, use force table to test outputs

2. Timer not timing correctly
   Fix: Check time base (1ms, 10ms, 100ms), verify preset value, ensure timer is being reset

3. Counter skipping counts
   Fix: Check input scan time vs pulse width, use high-speed counter input for fast signals

4. Communication lost intermittently
   Fix: Check network cables/switches, verify IP configuration, reduce communication rate, check for ground loops

5. Analog value jumping/noisy
   Fix: Add filtering (moving average), check shielding/grounding, verify wiring, check for EMI sources

6. Program runs slower than expected
   Fix: Optimize code (remove unnecessary instructions), check for infinite loops, reduce communication load

7. Value not updating in HMI
   Fix: Check tag scope (must be controller-scoped for HMI), verify HMI tag mapping, check communication

8. Safety relay not resetting
   Fix: Check all safety inputs (E-stops, guards), verify safety PLC program, check fault codes

9. Motor starts then stops immediately
   Fix: Check overload relay, verify VFD parameters, check for phase loss, inspect motor wiring

10. PID loop oscillating
    Fix: Tune PID parameters (start with P only, add I, then D), check feedback sensor, verify output scaling""",
        domain="plc",
        category="troubleshooting",
        tags=["plc", "errors", "debugging", "troubleshooting"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Output stuck: Use force table to bypass logic and test hardware",
            "Analog noise: Add 10ms filter: filtered := 0.9 * last + 0.1 * raw;",
            "Comm lost: Check cable with cable tester, verify switch configuration",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created PLC domain with {len(domain.entries)} entries")
    return domain
