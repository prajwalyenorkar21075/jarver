"""Actuators and Motors — knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_actuators_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="actuators",
        description="Actuators and motors — electric, hydraulic, and pneumatic actuators for robot motion, force generation, and manipulation.",
        subcategories=["dc_motors", "stepper", "servo", "brushless", "pneumatic", "hydraulic", "grippers", "control"],
    )

    domain.add_entry(KnowledgeEntry(
        id="actuators-overview-001",
        title="Actuator Types and Selection for Robotics",
        content="""Actuators convert energy into motion — the choice depends on required force, speed, precision, and environment.

Electric Actuators:

1. DC Motors (Brushed)
   - Speed: 100-10000 RPM
   - Torque: 0.01-100 Nm
   - Control: Voltage (speed), H-bridge (direction)
   - Pros: Simple, low cost, high speed
   - Cons: Brush wear, limited life (1000-5000 hours)
   - Use: Small robots, toys, simple conveyors

2. Brushless DC Motors (BLDC)
   - Speed: 1000-100000 RPM
   - Torque: 0.01-500 Nm
   - Control: ESC (Electronic Speed Controller), FOC (Field Oriented Control)
   - Pros: High efficiency (85-95%), long life (10000+ hours), high power density
   - Cons: Requires controller, more complex
   - Use: Drones, robot joints, CNC spindles

3. Stepper Motors
   - Speed: 100-1000 RPM (high torque at low speed)
   - Torque: 0.1-10 Nm
   - Control: Pulse train (1 pulse = 1 step, typically 1.8°/step = 200 steps/rev)
   - Pros: Open-loop positioning, high holding torque
   - Cons: Resonance, missed steps at high speed, power consumption
   - Use: 3D printers, CNC, pick-and-place

4. AC Servo Motors
   - Speed: 1000-6000 RPM
   - Torque: 0.1-1000 Nm
   - Control: Servo drive with encoder feedback
   - Pros: High precision, high dynamic response, regenerative braking
   - Cons: Expensive, requires tuning
   - Use: Industrial robots, CNC machines, precision positioning

Pneumatic Actuators:
- Speed: Very fast (0.1-1s stroke time)
- Force: 10-10000 N
- Control: On/off valves or proportional valves
- Pros: Simple, clean, explosion-proof, compliant
- Cons: Compressible air = imprecise positioning, requires compressor
- Use: Pick-and-place, clamping, pressing, packaging

Hydraulic Actuators:
- Speed: Slow to medium (0.5-5s stroke time)
- Force: 1000-1000000 N (very high force)
- Control: Servo valves for precise flow control
- Pros: Extremely high force density, stiff
- Cons: Oil leaks, maintenance, noise, heat generation
- Use: Heavy machinery, construction equipment, aircraft controls""",
        domain="actuators",
        category="overview",
        tags=["actuators", "motors", "selection", "electric", "pneumatic", "hydraulic"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "DC motor: 12V, 100RPM, 0.5Nm — small mobile robot drive",
            "BLDC: 48V, 3000RPM, 5Nm — robot arm joint with encoder",
            "Stepper: NEMA 23, 2.5A, 0.8Nm — 3D printer extruder",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="actuators-dc-001",
        title="DC Motors — Control and Interfacing",
        content="""DC motors are the simplest electric actuators — speed controlled by voltage, direction by polarity reversal.

DC Motor Types:
1. Brushed DC: Carbon brushes commutate current to rotor
2. Coreless/ironless: No cogging torque, fast response
3. Gear motors: Integrated gearbox (10:1 to 1000:1 reduction)
4. Linear actuators: Motor + lead screw (linear motion)

Motor Specifications:
- Rated voltage: 6V, 12V, 24V, 48V (nominal operating voltage)
- No-load speed: RPM at rated voltage with no load
- Stall torque: Maximum torque at 0 RPM (current limited)
- Rated torque: Continuous torque at rated speed
- Stall current: Current at stall (maximum, causes heating)
- Rated current: Current at rated torque/speed (continuous)

H-Bridge Control:
- 4 switches (MOSFETs or BJTs) in H configuration
- Forward: Q1+Q4 ON, Q2+Q3 OFF
- Reverse: Q2+Q3 ON, Q1+Q4 OFF
- Brake: Q1+Q2 ON (short motor terminals)
- Coast: All OFF (motor freewheels)

PWM Speed Control:
- Pulse Width Modulation: Vavg = duty_cycle × Vsupply
- Frequency: 10-20 kHz (above audible range)
- Duty cycle: 0-100% (0% = stopped, 100% = full speed)
- Microcontroller: Timer output PWM, H-bridge driver IC

Motor Drivers:
- L298N: Dual H-bridge, 2A per channel, 5-35V
- TB6612FNG: Dual H-bridge, 1.2A per channel, MOSFET (efficient)
- BTS7960: Single H-bridge, 43A, high-power applications
- Sabertooth: Dual 12A, serial/RC control, regenerative

Speed Feedback:
- Encoder: Quadrature pulses → RPM calculation
- Tachometer: Analog voltage proportional to speed
- Back-EMF: Measure motor voltage while coasting (sensorless)""",
        domain="actuators",
        category="dc_motors",
        tags=["actuators", "dc motor", "h-bridge", "pwm", "speed control"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["actuators-overview-001"],
        examples=[
            "PWM control: 50% duty cycle → 6V average from 12V supply",
            "H-bridge: L298N, IN1=HIGH, IN2=LOW → forward; IN1=LOW, IN2=HIGH → reverse",
            "Speed calculation: 1000 PPR encoder, 100 pulses in 0.1s → 6000 RPM",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="actuators-stepper-001",
        title="Stepper Motors — Precision Positioning",
        content="""Stepper motors move in discrete steps — open-loop positioning without encoder feedback, ideal for CNC, 3D printers, and pick-and-place.

Stepper Motor Types:
1. Bipolar: 4 wires, 2 coils, higher torque, requires H-bridge
2. Unipolar: 6 wires (center tap), simpler drive, lower torque
3. Hybrid: Permanent magnet rotor + toothed rotor, 1.8°/step (200 steps/rev)
4. Permanent magnet: Cheaper, lower resolution (7.5°-45°/step)

Step Modes:
- Full step: 1.8° per step (200 steps/rev) — maximum torque
- Half step: 0.9° per step (400 steps/rev) — smoother, less torque
- Microstepping: 1/4, 1/8, 1/16, 1/256 step — smoothest, lower torque
  - 1/16 microstep = 3200 steps/rev = 0.1125° resolution

Stepper Specifications:
- Step angle: 1.8° (standard), 0.9° (high-res), 7.5° (PM type)
- Holding torque: Torque with power applied, no motion (0.1-10 Nm)
- Detent torque: Torque with power off (magnetic cogging)
- Rated current: Per phase (0.5-5A typical)
- Phase resistance: 1-10Ω (limits current)
- Phase inductance: 1-10mH (limits current rise time)

Stepper Drivers:
- A4988: 2A, 8-35V, 1/16 microstep, STEP/DIR interface
- DRV8825: 2.5A, 8-45V, 1/32 microstep, STEP/DIR
- TB6600: 4A, 9-42V, 1/32 microstep, industrial
- Gecko G540: 4-axis, 4.25A, industrial CNC

Control Signals:
- STEP: Pulse (rising edge = one step)
- DIR: HIGH = clockwise, LOW = counterclockwise
- EN: Enable (LOW = enabled, HIGH = disabled)
- Pulse rate: Steps per second → RPM = (pps × 60) / steps_per_rev

Speed/Torque Curve:
- Torque drops rapidly with speed (inductance limits current)
- Peak power at ~50% of no-load speed
- Use microstepping for smooth low-speed operation
- Use gear reduction for high torque at low speed""",
        domain="actuators",
        category="stepper",
        tags=["actuators", "stepper", "positioning", "cnc", "3d printer"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["actuators-overview-001"],
        examples=[
            "NEMA 17: 1.8°/step, 0.4Nm holding, 1.5A/phase — 3D printer extruder",
            "Microstepping: 1/16 → 3200 steps/rev = 0.1125° resolution",
            "Speed: 1000 pulses/sec, 200 steps/rev → 300 RPM",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="actuators-servo-001",
        title="Servo Motors — Closed-Loop Precision Motion",
        content="""Servo motors use encoder feedback for precise position, velocity, and torque control — the standard for industrial robots and CNC.

Servo Motor Types:
1. AC Servo: Brushless AC motor + encoder + servo drive
   - Power: 100W to 100kW
   - Speed: 1000-6000 RPM rated, up to 10000 RPM peak
   - Torque: 0.1-1000 Nm continuous, 3x peak for short duration
   - Voltage: 200-480V AC (3-phase industrial)

2. DC Servo: Brushed or brushless DC motor + encoder
   - Power: 10W to 10kW
   - Speed: 1000-5000 RPM
   - Voltage: 24-96V DC (mobile robots, AGVs)

Servo Drive Functions:
- Commutation: Electronic switching for BLDC motors (6-step or FOC)
- Current loop: Torque control (fastest loop, 10-20kHz)
- Velocity loop: Speed control (1-5kHz)
- Position loop: Position control (100-1000Hz)
- Trajectory generation: Smooth motion profiles (trapezoidal, S-curve)

Feedback Devices:
- Incremental encoder: 1000-10000 PPR, relative position
- Absolute encoder: 16-23 bit, absolute position (no homing)
- Resolver: Analog, robust (high vibration, temperature)
- Sin/cos encoder: High resolution (interpolation to 1M counts/rev)

Servo Tuning:
- Gain scheduling: Different gains for different speeds/loads
- Auto-tuning: Drive measures load inertia, sets gains automatically
- Manual tuning: Adjust P (stiffness), I (eliminate steady-state error), D (damping)
- Bode plot: Frequency response analysis for stability

Communication:
- Analog: ±10V command (velocity or torque mode)
- Pulse/Direction: Step commands (like stepper)
- Digital buses: EtherCAT, PROFINET, CANopen, Modbus
- ROS2: ros2_control, hardware_interface, JointTrajectoryController

Common Brands:
- Yaskawa (Sigma-7), Siemens (SIMOTICS S), Fanuc, Mitsubishi
- Delta, Omron, Beckhoff, Kollmorgen, Trinamic""",
        domain="actuators",
        category="servo",
        tags=["actuators", "servo", "closed-loop", "industrial", "precision"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["actuators-dc-001"],
        examples=[
            "Yaskawa SGMJV-04A: 400W, 3000RPM, 1.27Nm, 20-bit absolute encoder",
            "Tuning: Increase P gain until oscillation, then reduce by 50%",
            "EtherCAT: 1ms cycle time, 100 servos on single network",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="actuators-pneumatic-001",
        title="Pneumatic Actuators — Fast, Compliant Motion",
        content="""Pneumatic actuators use compressed air for fast, forceful motion — ideal for pick-and-place, clamping, and applications requiring compliance.

Pneumatic Actuator Types:

1. Linear Cylinders
   - Single-acting: Air extends, spring returns (or gravity)
   - Double-acting: Air extends and retracts
   - Bore sizes: 10mm to 320mm (force: 10N to 50kN at 6 bar)
   - Stroke: 10mm to 2000mm typical
   - Speed: 0.1-1m/s (adjustable with flow controls)

2. Rotary Actuators
   - Rack-and-pinion: Linear cylinder rotates shaft (90°, 180°, 360°)
   - Vane type: Air pushes vane in chamber (limited angle)
   - Torque: 1-1000 Nm

3. Grippers
   - Parallel: Two fingers move symmetrically
   - Angular: Fingers rotate open/close
   - 3-point: Centering grip for round objects
   - Force: 10-500N per finger

Pneumatic Components:
- Compressor: Generates compressed air (0.5-10 bar, 50-1000 L/min)
- FRL (Filter-Regulator-Lubricator): Cleans air, sets pressure, oils mist
- Valves: 5/2 (5 ports, 2 positions), 3/2, 2/2 — solenoid actuated
- Flow controls: Meter-in (slow extend), meter-out (slow retract)
- Sensors: Reed switches (magnet on piston), proximity sensors

Control:
- On/off: Solenoid valve (extend/retract)
- Proportional: Proportional valve (variable speed/force)
- Servo-pneumatic: Closed-loop position control (expensive, complex)

Advantages:
- Very fast (0.1-0.5s cycle time)
- Clean (no oil leaks, safe for food/pharma)
- Explosion-proof (no sparks)
- Compliant (soft stop at end of stroke)
- Simple, reliable, low cost

Disadvantages:
- Compressible air = imprecise positioning
- Requires compressor (energy inefficient, ~10% electrical efficiency)
- Noisy (exhaust air, use mufflers)
- Force varies with position (pressure drop)""",
        domain="actuators",
        category="pneumatic",
        tags=["actuators", "pneumatic", "cylinder", "gripper", "compressed air"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["actuators-overview-001"],
        examples=[
            "Cylinder: 50mm bore, 100mm stroke, 6 bar → 1178N force (F = P × A)",
            "Valve: 5/2 solenoid, 24VDC, 100ms switching time",
            "Speed control: Meter-out flow control → smooth, stable motion",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="actuators-grippers-001",
        title="Robot Grippers — End-of-Arm Tooling",
        content="""Robot grippers (end-effectors) grasp and manipulate objects — the choice depends on object shape, weight, surface, and required precision.

Gripper Types:

1. Mechanical Grippers
   - Parallel: Two fingers move symmetrically (constant grip width)
   - Angular: Fingers rotate (width changes with angle)
   - 3-point: Three fingers center round objects
   - Force: 50-2000N, stroke: 0-150mm
   - Actuation: Pneumatic (fast), electric (precise), hydraulic (high force)

2. Vacuum Grippers (Suction Cups)
   - Principle: Vacuum creates pressure differential
   - Types: Flat (smooth surfaces), bellows (uneven surfaces), oval (elongated)
   - Sizes: 10-200mm diameter (force: 10-5000N per cup)
   - Vacuum generator: Venturi (compressed air) or electric pump
   - Best for: Flat, smooth, non-porous surfaces (glass, metal, plastic)

3. Magnetic Grippers
   - Permanent magnet: Always on (requires mechanical release)
   - Electromagnet: Switchable (power on/off)
   - Electro-permanent: Pulse to switch (energy efficient)
   - Best for: Ferromagnetic materials (steel, iron)

4. Soft Grippers
   - Compliant fingers (silicone, rubber)
   - Adaptive: Conform to object shape
   - Gentle: Safe for fragile objects (fruit, eggs)
   - Types: Pneumatic networks (pne-nets), tendon-driven, granular jamming

5. Specialized EOAT (End-of-Arm Tools)
   - Welding torches (MIG, TIG, spot)
   - Dispensing (glue, sealant, solder)
   - Sanding/grinding (spindle with abrasive)
   - Inspection (camera, laser scanner, force sensor)

Gripper Selection:
- Object weight: Gripper force > 3x weight (safety factor)
- Object shape: Parallel (box), 3-point (cylinder), suction (flat)
- Surface: Smooth (suction), rough (mechanical), delicate (soft)
- Cycle time: Pneumatic (fastest), electric (slower but precise)
- Environment: Clean (pneumatic), wet (stainless steel), explosive (pneumatic)""",
        domain="actuators",
        category="grippers",
        tags=["actuators", "gripper", "end-effector", "manipulation", "grasping"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["actuators-overview-001"],
        examples=[
            "Parallel gripper: Robotiq 2F-85, 85mm stroke, 235N force, electric",
            "Suction cup: 60mm diameter, -60kPa vacuum → 169N force (F = P × A)",
            "Soft gripper: Festo DMLA, 3 fingers, compliant grip for fragile objects",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Actuators domain with {len(domain.entries)} entries")
    return domain
