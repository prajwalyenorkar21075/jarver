"""C++ for Robotics — knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_cpp_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="cpp",
        description="C++ programming for robotics — high-performance control, embedded systems, ROS2 nodes, and real-time processing.",
        subcategories=["basics", "memory", "oop", "stl", "realtime", "embedded", "ros2cpp"],
    )

    domain.add_entry(KnowledgeEntry(
        id="cpp-basics-001",
        title="C++ Basics for Robotics",
        content="""C++ is the standard language for high-performance robotics — used in ROS2, embedded controllers, motion planning, and real-time systems.

Key concepts:
- Variables, types, pointers, references
- Classes, inheritance, polymorphism (for robot components)
- Templates for generic sensor/actuator interfaces
- RAII (Resource Acquisition Is Initialization) for safe resource management
- Smart pointers (unique_ptr, shared_ptr) for memory safety

Robotics-specific patterns:
- Use const references to avoid copying large data (sensor frames, point clouds)
- Use Eigen library for linear algebra (kinematics, transformations)
- Use std::chrono for precise timing in control loops
- Use std::thread and std::mutex for concurrent operations
- Use std::vector and std::array for fixed-size robot data""",
        domain="cpp",
        category="basics",
        tags=["cpp", "c++", "basics", "robotics"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "const auto& cloud = getPointCloud(); // avoid copy",
            "std::unique_ptr<Sensor> sensor = std::make_unique<LidarSensor>();",
            "Eigen::Matrix4d T = Eigen::Matrix4d::Identity(); // transformation matrix",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="cpp-memory-001",
        title="Memory Management and Smart Pointers",
        content="""Proper memory management is critical in robotics — leaks cause crashes in long-running robot systems.

Smart pointers (preferred over raw new/delete):
- std::unique_ptr<T>: Exclusive ownership, auto-deleted when out of scope
- std::shared_ptr<T>: Shared ownership, deleted when last owner releases
- std::weak_ptr<T>: Non-owning reference to shared_ptr data

RAII pattern:
- Resources acquired in constructor, released in destructor
- File handles, mutex locks, network connections all follow RAII
- std::lock_guard<std::mutex> for automatic mutex unlock

Robotics applications:
- unique_ptr for sensor objects owned by robot controller
- shared_ptr for shared point cloud data between processing nodes
- weak_ptr for observer patterns (sensor listeners)
- Always prefer make_unique/make_shared over raw new""",
        domain="cpp",
        category="memory",
        tags=["cpp", "memory", "smart pointers", "RAII"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["cpp-basics-001"],
        examples=[
            "auto lidar = std::make_unique<LidarSensor>(port); // unique ownership",
            "auto cloud = std::make_shared<PointCloud>(); // shared between nodes",
            "std::lock_guard<std::mutex> lock(mutex); // auto-unlock",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="cpp-eigen-001",
        title="Eigen Library — Linear Algebra for Robotics",
        content="""Eigen is the standard C++ library for linear algebra in robotics — used in kinematics, control, SLAM, and motion planning.

Core types:
- Eigen::Vector2d, Vector3d, Vector4d: Fixed-size vectors
- Eigen::Matrix3d, Matrix4d: Fixed-size matrices
- Eigen::MatrixXd, VectorXd: Dynamic-size
- Eigen::Quaterniond: Rotation representation

Key operations:
- Matrix multiplication: C = A * B
- Transpose: A.transpose()
- Inverse: A.inverse()
- Cross product: a.cross(b)
- Norm: a.norm()

Robotics applications:
- Homogeneous transformations (4x4 matrices)
- Forward/inverse kinematics (Jacobian matrices)
- Rotation representations (quaternions, rotation matrices, Euler angles)
- Kalman filter state estimation
- Point cloud transformations""",
        domain="cpp",
        category="stl",
        tags=["cpp", "eigen", "linear algebra", "matrices", "kinematics"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["cpp-basics-001"],
        examples=[
            "Eigen::Matrix4d T = Eigen::Matrix4d::Identity(); T.block<3,3>(0,0) = R; T.block<3,1>(0,3) = t;",
            "Eigen::Quaterniond q(w, x, y, z); Eigen::Matrix3d R = q.toRotationMatrix();",
            "Eigen::Vector3d result = J * dq; // Jacobian * joint velocities",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="cpp-realtime-001",
        title="Real-Time Programming in C++",
        content="""Real-time programming ensures robot control loops execute within deterministic time bounds — critical for stability and safety.

Key concepts:
- Hard real-time: Missing deadline = system failure (motor control)
- Soft real-time: Occasional misses acceptable (UI updates)
- std::chrono::high_resolution_clock for precise timing
- std::this_thread::sleep_until() for periodic loops
- Thread priorities with pthread or std::thread attributes

Real-time patterns:
- Fixed-rate control loop: measure execution time, sleep for remainder
- Lock-free data structures for inter-thread communication
- std::atomic for thread-safe counters and flags
- Avoid dynamic allocation (new/malloc) in control loops
- Use pre-allocated buffers for sensor data

Linux real-time:
- chrt -r 99 ./robot_node for real-time scheduling
- mlockall() to prevent page faults
- Disable CPU frequency scaling for consistent timing""",
        domain="cpp",
        category="realtime",
        tags=["cpp", "real-time", "control loop", "deterministic"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["cpp-basics-001"],
        examples=[
            "auto next = std::chrono::steady_clock::now() + period; while(running) { doControl(); std::this_thread::sleep_until(next); next += period; }",
            "std::atomic<bool> emergency_stop{false}; // lock-free flag",
            "chrt -r 99 ./motor_controller // Linux real-time priority",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="cpp-troubleshoot-001",
        title="Common C++ Robotics Errors and Fixes",
        content="""Frequent C++ errors in robotics code and their solutions:

1. Segmentation fault (segfault)
   Fix: Check null pointers, array bounds, use smart pointers, run with valgrind or AddressSanitizer

2. Undefined reference to vtable
   Fix: Ensure all virtual methods have implementations, check linker flags

3. Memory leak in long-running robot
   Fix: Use smart pointers, check for raw new without delete, use RAII

4. Eigen: THIS_METHOD_IS_ONLY_FOR_DYNAMIC_SIZED_MATRICES
   Fix: Use fixed-size methods (rows(), cols()) not dynamic ones (resize())

5. Thread deadlock
   Fix: Always lock mutexes in same order, use std::lock_guard, avoid nested locks

6. ROS2 node crashes on startup
   Fix: Check rclcpp::init() called before node creation, verify QoS settings match publishers/subscribers

7. CMake: target not found
   Fix: find_package(Eigen3 REQUIRED), target_link_libraries(node ${Eigen3_LIBS})""",
        domain="cpp",
        category="troubleshooting",
        tags=["cpp", "errors", "debugging", "segfault", "memory"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "Segfault: compile with -fsanitize=address to find exact location",
            "Memory leak: use std::unique_ptr instead of raw new",
            "Eigen mismatch: use .resize() only on Dynamic-size matrices",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created C++ domain with {len(domain.entries)} entries")
    return domain
