"""Python for Robotics — knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_python_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="python",
        description="Python programming for robotics — scripting, libraries, patterns, and best practices for robot software development.",
        subcategories=["basics", "numpy", "opencv", "ros2py", "asyncio", "hardware", "patterns"],
    )

    domain.add_entry(KnowledgeEntry(
        id="py-basics-001",
        title="Python Basics for Robotics",
        content="""Python is the primary language for robotics prototyping, AI/ML integration, and high-level robot control.

Key concepts for robotics:
- Variables, data types, control flow (if/else, loops)
- Functions and classes (OOP for robot modules)
- Lists, dicts, tuples for sensor data storage
- Error handling (try/except) for robust robot code
- File I/O for configuration and data logging

Robotics-specific patterns:
- Use dataclasses for sensor readings and robot state
- Use enums for robot modes (IDLE, MOVING, GRIPPING, ERROR)
- Use type hints for clarity in team projects
- Use logging module instead of print() for production code""",
        domain="python",
        category="basics",
        tags=["python", "basics", "robotics", "programming"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Use dataclass for SensorReading: temperature, timestamp, unit",
            "Use Enum for RobotState: IDLE, MOVING, PICKING, PLACING, ERROR",
            "Use logging.getLogger(__name__) for module-level logging",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="py-numpy-001",
        title="NumPy for Robotics — Arrays and Math",
        content="""NumPy is essential for robotics — used in sensor data processing, kinematics, path planning, and computer vision.

Core concepts:
- np.array() for creating vectors and matrices
- np.zeros(), np.ones(), np.eye() for initialization
- Array slicing: data[start:end:step]
- Broadcasting: operations between arrays of different shapes
- np.dot(), @ operator for matrix multiplication

Robotics applications:
- Homogeneous transformation matrices (4x4)
- Joint angle arrays for robot arms
- Point clouds from LiDAR/depth sensors
- Image data as 2D/3D arrays
- PID controller calculations""",
        domain="python",
        category="numpy",
        tags=["numpy", "math", "arrays", "matrices", "kinematics"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["py-basics-001"],
        examples=[
            "Transformation matrix: T = np.array([[R, t], [0, 1]]) where R is 3x3 rotation, t is 3x1 translation",
            "Joint angles: joints = np.array([0.0, -1.57, 0.0, -1.57, 0.0, 0.0]) for 6-DOF arm",
            "Point cloud: points = np.random.rand(1000, 3) for 1000 3D points",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="py-asyncio-001",
        title="Asyncio for Concurrent Robot Tasks",
        content="""Asyncio enables concurrent operations in Python — essential for robots that need to handle sensor reading, motor control, and communication simultaneously.

Key concepts:
- async/await syntax for coroutines
- asyncio.run() to start the event loop
- asyncio.gather() to run multiple tasks concurrently
- asyncio.create_task() for fire-and-forget tasks
- asyncio.sleep() for non-blocking delays

Robotics patterns:
- Sensor polling loop as async coroutine
- Motor command queue with async processing
- WebSocket communication with async handlers
- Async MQTT/ROS2 message handling
- Parallel image processing pipelines""",
        domain="python",
        category="asyncio",
        tags=["asyncio", "concurrency", "async", "coroutines"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["py-basics-001"],
        examples=[
            "async def read_sensors(): while True: data = await sensor.read(); await asyncio.sleep(0.01)",
            "results = await asyncio.gather(read_lidar(), read_camera(), read_imu())",
            "asyncio.create_task(monitor_battery()) for background monitoring",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="py-opencv-001",
        title="OpenCV with Python — Computer Vision Basics",
        content="""OpenCV (cv2) is the standard library for computer vision in robotics — used for object detection, navigation, inspection, and manipulation.

Core operations:
- cv2.imread() / cv2.VideoCapture() for image input
- cv2.cvtColor() for color space conversion (BGR, RGB, HSV, GRAY)
- cv2.threshold() / cv2.inRange() for binary masking
- cv2.findContours() for object boundary detection
- cv2.resize() / cv2.warpAffine() for image transformation

Robotics applications:
- Color-based object tracking (HSV filtering)
- ArUco marker detection for robot localization
- Line following with thresholding and contour analysis
- Blob detection for pick-and-place targets
- Depth estimation from stereo cameras""",
        domain="python",
        category="opencv",
        tags=["opencv", "cv2", "computer vision", "image processing"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["py-numpy-001"],
        examples=[
            "Color filter: hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV); mask = cv2.inRange(hsv, lower, upper)",
            "Contour detection: contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)",
            "Camera capture: cap = cv2.VideoCapture(0); ret, frame = cap.read()",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="py-serial-001",
        title="Serial Communication with Arduino/Microcontrollers",
        content="""Python's pyserial library enables communication with Arduino, ESP32, and other microcontrollers over serial/USB.

Setup:
- pip install pyserial
- import serial

Key operations:
- serial.Serial(port, baudrate, timeout) to open connection
- ser.write(data.encode()) to send data
- ser.readline().decode().strip() to read line
- ser.close() to release port

Common patterns:
- Send commands as JSON strings for structured data
- Use newline delimiters for message framing
- Implement handshake protocol for reliable connection
- Handle serial exceptions for disconnects
- Use threading or asyncio for non-blocking reads""",
        domain="python",
        category="hardware",
        tags=["serial", "arduino", "microcontroller", "communication", "pyserial"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["py-basics-001"],
        examples=[
            "ser = serial.Serial('COM3', 115200, timeout=1); ser.write(b'START\\n')",
            "response = ser.readline().decode().strip() # Read until newline",
            "Use struct.pack() for binary data: struct.pack('fff', x, y, z)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="py-troubleshoot-001",
        title="Common Python Robotics Errors and Fixes",
        content="""Frequent errors in Python robotics code and their solutions:

1. ImportError: No module named 'cv2'
   Fix: pip install opencv-python (or opencv-python-headless for servers)

2. SerialException: Could not connect to port
   Fix: Check port name (COM3 vs /dev/ttyUSB0), ensure user has permissions, close other programs using the port

3. MemoryError with large images/point clouds
   Fix: Process in chunks, use np.float32 instead of float64, release arrays with del()

4. Camera returns None/empty frames
   Fix: Check camera index (0, 1, 2...), add retry logic, ensure camera is not in use by another process

5. Asyncio 'Task was destroyed but it is pending'
   Fix: await all tasks before exiting, use asyncio.gather() for cleanup

6. NumPy shape mismatch in matrix operations
   Fix: Print shapes with arr.shape, use .reshape() or .transpose() to match dimensions""",
        domain="python",
        category="troubleshooting",
        tags=["python", "errors", "debugging", "troubleshooting"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "cv2 not found: pip install opencv-python",
            "Serial port busy: sudo lsof | grep ttyUSB (Linux) or check Device Manager (Windows)",
            "Empty camera frame: for _ in range(10): ret, frame = cap.read(); if ret: break",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Python domain with {len(domain.entries)} entries")
    return domain
