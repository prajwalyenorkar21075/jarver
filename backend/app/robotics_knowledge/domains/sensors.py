"""Sensors — knowledge domain for robotics sensors and measurement."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_sensors_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="sensors",
        description="Robotics sensors — types, principles, interfacing, and signal processing for position, distance, force, temperature, and environmental measurement.",
        subcategories=["proximity", "distance", "force_torque", "imu", "encoders", "vision", "temperature", "interfacing"],
    )

    domain.add_entry(KnowledgeEntry(
        id="sensors-overview-001",
        title="Sensor Types and Selection for Robotics",
        content="""Sensors convert physical quantities into electrical signals — essential for robot perception, feedback control, and environmental awareness.

Sensor Categories:

1. Proximity/Presence Sensors
   - Inductive: Detect metal objects (2-30mm range)
   - Capacitive: Detect any material (metal, plastic, liquid)
   - Photoelectric: Beam break, reflective, diffuse (up to 10m)
   - Ultrasonic: Sound waves (20mm to 10m, any material)

2. Distance/Position Sensors
   - LiDAR: Laser range finding (0.1m to 100m+, 2D/3D)
   - Ultrasonic: Sound time-of-flight (20mm to 5m)
   - IR range: Infrared triangulation (4-30cm typical)
   - Encoders: Rotary/linear position (incremental/absolute)
   - Potentiometers: Analog position (0-10kΩ, limited life)
   - LVDT: Linear variable differential transformer (high precision)

3. Force/Torque Sensors
   - Strain gauge: Load cells (0-100kN typical)
   - Piezoelectric: Dynamic force measurement
   - Capacitive: High-resolution force/torque (6-axis)
   - Tactile arrays: Pressure distribution (robot grippers)

4. Inertial Sensors
   - Accelerometer: Linear acceleration (±2g to ±200g)
   - Gyroscope: Angular velocity (±125°/s to ±2000°/s)
   - IMU: Combined accel + gyro + magnetometer (9-DOF)
   - GPS: Absolute position (outdoor, ±1-5m accuracy)

5. Environmental Sensors
   - Temperature: Thermocouple, RTD, thermistor
   - Pressure: Barometric, differential, absolute
   - Humidity: Capacitive, resistive
   - Gas: CO, CO2, O2, combustible gases

Selection Criteria:
- Range: Min/max measurement values
- Resolution: Smallest detectable change
- Accuracy: Closeness to true value (±% of full scale)
- Repeatability: Same output for same input
- Response time: How fast sensor reacts to changes
- Environment: Temperature, vibration, EMI, IP rating
- Interface: Analog (0-10V, 4-20mA), digital (I2C, SPI, RS485)""",
        domain="sensors",
        category="overview",
        tags=["sensors", "types", "selection", "measurement"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Inductive proximity: Detect metal parts on conveyor (2-30mm range)",
            "LiDAR: RPLIDAR A1 (360° scan, 12m range, 8000 pts/s)",
            "6-axis F/T sensor: ATI Gamma IP-65 (robot wrist force sensing)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="sensors-encoders-001",
        title="Encoders — Position and Speed Feedback",
        content="""Encoders measure rotary or linear position — used in motor feedback, joint angle measurement, and precision positioning.

Encoder Types:

1. Incremental Encoders
   - Output: Pulse train (A, B channels, optional Z index)
   - Resolution: 100-10000 pulses per revolution (PPR)
   - Quadrature: A and B 90° out of phase → direction detection
   - Index pulse: One pulse per revolution (Z channel) → reference position
   - Counting: 1x (A only), 2x (A+B edges), 4x (all edges) → resolution multiplier
   - Interface: Differential line driver (RS422) for noise immunity

2. Absolute Encoders
   - Output: Digital word (binary, Gray code, SSI, BiSS)
   - Single-turn: 8-16 bits (256-65536 positions per revolution)
   - Multi-turn: Tracks revolutions (battery or gear-based)
   - No homing required — position known immediately on power-up
   - Communication: SSI (Synchronous Serial Interface), BiSS-C, CANopen

3. Linear Encoders
   - Measure linear position directly (no ball screw backlash)
   - Scale with glass/metal tape, reading head with photodiodes
   - Resolution: 0.1μm to 10μm typical
   - Used in CNC machines, CMMs, precision stages

Encoder Interfacing:
- Microcontroller: Timer/counter input, interrupt on A edge, read B for direction
- PLC: High-speed counter module (HSC), configure for 4x counting
- Motion controller: Dedicated encoder input, hardware quadrature decoding

Common Issues:
- Missed counts: Increase counter speed, use differential signals
- Noise: Shielded cables, twisted pair, proper grounding
- Vibration: Mount encoder rigidly, use flexible coupling
- Resolution: 4x counting, interpolate between pulses""",
        domain="sensors",
        category="encoders",
        tags=["sensors", "encoders", "position", "feedback", "quadrature"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["sensors-overview-001"],
        examples=[
            "Incremental: 1000 PPR, 4x counting = 4000 counts/rev = 0.09° resolution",
            "Absolute: 16-bit single-turn = 65536 positions = 0.0055° resolution",
            "Linear: 1μm resolution, 1m travel, glass scale with reading head",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="sensors-lidar-001",
        title="LiDAR — Laser Range Finding for Navigation",
        content="""LiDAR (Light Detection and Ranging) uses laser pulses to measure distance — essential for mobile robot navigation, mapping, and obstacle avoidance.

LiDAR Types:

1. 2D LiDAR (Planar)
   - Scans single horizontal plane (360° typical)
   - Range: 0.1m to 30m (indoor), up to 100m+ (outdoor)
   - Scan rate: 5-20 Hz (frames per second)
   - Points per scan: 1000-20000
   - Examples: RPLIDAR A1/A2, Hokuyo URG-04LX, SICK TiM561

2. 3D LiDAR
   - Scans 3D volume (multiple layers or rotating mirror)
   - Range: 0.5m to 200m
   - Points per second: 100k to 2M+
   - Examples: Velodyne VLP-16 (16-layer), Ouster OS1-64, Livox Mid-40

3. Solid-State LiDAR
   - No moving parts (MEMS mirrors, optical phased arrays)
   - More robust, compact, lower cost
   - Limited FOV (120° typical) vs rotating (360°)
   - Examples: Intel RealSense L515, LeddarVu8

LiDAR Data:
- Point cloud: (x, y, z) coordinates + intensity
- ROS2 message: sensor_msgs/PointCloud2
- Processing: PCL (Point Cloud Library), Open3D

Applications:
- SLAM (Simultaneous Localization and Mapping)
- Obstacle detection and avoidance
- Object recognition and classification
- Map building (2D occupancy grid, 3D point cloud map)
- People tracking (leg detection, pose estimation)

Interfacing:
- Ethernet (most common): 100Mbps, TCP/UDP
- USB: For low-cost 2D LiDAR
- ROS2 driver: rplidar_ros, velodyne_driver, ouster_ros""",
        domain="sensors",
        category="distance",
        tags=["sensors", "lidar", "laser", "navigation", "slam", "point cloud"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["sensors-overview-001"],
        examples=[
            "RPLIDAR A1: 360° scan, 12m range, 8000 pts/s, $100",
            "Velodyne VLP-16: 360°x30° FOV, 100m range, 300k pts/s, $4000",
            "ROS2: ros2 run rplidar_ros rplidar_node --ros-args -p serial_port:=/dev/ttyUSB0",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="sensors-imu-001",
        title="IMU — Inertial Measurement Units",
        content="""IMUs measure linear acceleration and angular velocity — used for robot orientation, motion tracking, and sensor fusion with GPS/odometry.

IMU Components:

1. Accelerometer (3-axis)
   - Measures: Linear acceleration (±2g to ±200g)
   - Principle: MEMS capacitive or piezoelectric
   - Output: Acceleration in m/s² or g (9.81 m/s² = 1g)
   - Static: Measures gravity → tilt estimation
   - Dynamic: Measures motion, vibration, shock

2. Gyroscope (3-axis)
   - Measures: Angular velocity (±125°/s to ±2000°/s)
   - Principle: MEMS vibrating structure (Coriolis effect)
   - Output: Angular rate in °/s or rad/s
   - Integration: Angular position (drifts over time)
   - Used for: Fast rotation detection, stabilization

3. Magnetometer (3-axis)
   - Measures: Magnetic field strength (±0.3 to ±8 Gauss)
   - Principle: Hall effect or magnetoresistive
   - Output: Magnetic field in μT or Gauss
   - Used for: Compass heading (yaw), heading reference
   - Issues: Magnetic interference (motors, metal structures)

IMU Specifications:
- MPU-6050: 6-DOF (accel + gyro), I2C, $2 (hobby)
- BNO055: 9-DOF (accel + gyro + mag), built-in sensor fusion, I2C
- BMI088: 6-DOF, high-performance, SPI, $10
- VectorNav VN-100: 9-DOF, RTK GPS, $1000+ (industrial)

Sensor Fusion:
- Complementary filter: Simple, low CPU (accel + gyro)
- Kalman filter: Optimal estimation, more complex (accel + gyro + mag)
- Madgwick filter: Efficient, drift-free orientation
- EKF/UKF: Extended/Unscented Kalman for nonlinear systems

ROS2 Integration:
- sensor_msgs/Imu message: orientation, angular_velocity, linear_acceleration
- Covariance matrices for each measurement
- IMU driver: imu_bno055, ros_imu_bno055""",
        domain="sensors",
        category="imu",
        tags=["sensors", "imu", "accelerometer", "gyroscope", "orientation"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["sensors-overview-001"],
        examples=[
            "MPU-6050: I2C address 0x68, read accel_x, gyro_z registers",
            "Sensor fusion: Madgwick filter for drift-free orientation (roll, pitch, yaw)",
            "ROS2: ros2 run imu_bno055 bno055_node --ros-args -p i2c_bus:=1",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="sensors-force-001",
        title="Force/Torque Sensors for Robot Manipulation",
        content="""Force/torque (F/T) sensors measure contact forces — essential for compliant manipulation, assembly, grinding, and human-robot interaction.

F/T Sensor Types:

1. Strain Gauge Load Cells
   - Principle: Metal element deforms under load, strain gauges measure deformation
   - Configuration: Full bridge (4 gauges) for temperature compensation
   - Capacity: 0-100kN (industrial), 0-10N (precision)
   - Accuracy: ±0.03% of full scale (high-end)
   - Axes: Single-axis (compression/tension) or multi-axis (3-force, 3-torque)

2. 6-Axis F/T Sensors (Robot Wrist)
   - Measure: 3 forces (Fx, Fy, Fz) + 3 torques (Tx, Ty, Tz)
   - Mounting: Between robot last link and tool (wrist-mounted)
   - Capacity: ±10kN forces, ±500Nm torques typical
   - Examples: ATI Gamma, OnRobot RT, Robotiq FT300
   - Interface: Ethernet, EtherCAT, analog

3. Tactile Sensors (Gripper)
   - Measure: Pressure distribution across contact surface
   - Resolution: 4x4 to 12x12 taxels (tactile pixels) typical
   - Range: 0-20 N per taxel
   - Examples: Robotiq Tactile, SynTouch BioTac, GelSight
   - Used for: Grasp stability, slip detection, object recognition

F/T Sensor Applications:
- Peg-in-hole assembly: Force-guided insertion
- Surface following: Maintain constant contact force (grinding, polishing)
- Gripping: Detect slip, adjust grip force
- Human interaction: Detect contact, stop or comply
- Quality inspection: Measure insertion force profile

Signal Processing:
- Gravity compensation: Subtract tool weight from Fz
- Filtering: Low-pass filter (10-50Hz cutoff) to remove noise
- Thresholding: Detect contact (F > threshold)
- Impedance control: Force → position adjustment (stiffness, damping)

ROS2 Integration:
- geometry_msgs/WrenchStamped: force (x,y,z) + torque (x,y,z)
- Calibration: Zero sensor on startup, apply known weights
- Driver: ati_ft_sensor, robotiq_ft_sensor""",
        domain="sensors",
        category="force_torque",
        tags=["sensors", "force", "torque", "manipulation", "compliance"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["sensors-overview-001"],
        examples=[
            "ATI Gamma: 6-axis, ±145N forces, ±10Nm torques, Ethernet interface",
            "Grasp control: Increase grip force until F/T shows no slip (Fz stable)",
            "Assembly: Force-guided peg insertion with 10N compliance in X/Y",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="sensors-interfacing-001",
        title="Sensor Interfacing — Analog and Digital",
        content="""Sensor interfacing connects physical sensors to controllers (PLC, microcontroller, PC) — analog voltage/current, digital protocols, and signal conditioning.

Analog Interfaces:

1. Voltage (0-10V)
   - Common: Position, pressure, temperature
   - Resolution: 10-bit ADC = 1024 steps = 10mV per step
   - Wiring: 3 wires (signal, ground, shield)
   - Issues: Voltage drop over long cables (>10m), noise pickup

2. Current Loop (4-20mA)
   - Common: Industrial sensors (pressure, temperature, flow)
   - Advantage: Immune to voltage drop, works over 100m+
   - Wiring: 2 wires (loop powered) or 3 wires
   - Zero: 4mA (not 0mA) → detect wire break (0mA = fault)
   - Scaling: 4mA = 0%, 20mA = 100% of range

3. Resistance (RTD, Thermistor)
   - RTD: Pt100 (100Ω at 0°C), linear, -200 to +850°C
   - Thermistor: 10kΩ at 25°C, nonlinear, -50 to +150°C
   - Measurement: Voltage divider, Wheatstone bridge
   - ADC: Measure voltage, calculate resistance, convert to temperature

Digital Interfaces:

1. I2C (Inter-IC Communication)
   - 2 wires: SDA (data), SCL (clock)
   - Speed: 100kHz (standard), 400kHz (fast)
   - Distance: <1m (on PCB)
   - Address: 7-bit (128 devices) or 10-bit
   - Common: IMU, barometer, temperature sensors

2. SPI (Serial Peripheral Interface)
   - 4 wires: MOSI, MISO, SCK, CS
   - Speed: 1-50 MHz (much faster than I2C)
   - Distance: <1m (on PCB)
   - Full-duplex: Send and receive simultaneously
   - Common: High-speed ADC, encoders, IMU

3. RS-485 / Modbus RTU
   - 2 wires (half-duplex) or 4 wires (full-duplex)
   - Distance: Up to 1200m
   - Speed: 9600 to 115200 baud
   - Devices: Up to 247 on single bus
   - Common: Industrial sensors, motor drives, power meters

Signal Conditioning:
- Amplification: Increase small signals (strain gauge, thermocouple)
- Filtering: Remove noise (low-pass, band-pass)
- Isolation: Protect controller from high voltage (opto-isolators)
- Linearization: Convert nonlinear sensor output to linear scale""",
        domain="sensors",
        category="interfacing",
        tags=["sensors", "analog", "digital", "i2c", "spi", "4-20ma", "interfacing"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["sensors-overview-001"],
        examples=[
            "4-20mA: Pressure sensor 0-100 PSI → 4mA=0 PSI, 20mA=100 PSI",
            "I2C: MPU-6050 at address 0x68, read 14 registers for accel+gyro",
            "RS-485: Modbus RTU, poll 10 sensors every 100ms = 10Hz update rate",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Sensors domain with {len(domain.entries)} entries")
    return domain
