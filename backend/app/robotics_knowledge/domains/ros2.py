"""ROS2 — Robot Operating System 2 knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_ros2_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="ros2",
        description="ROS2 (Robot Operating System 2) — the standard middleware for robot software architecture. Covers nodes, topics, services, actions, and best practices.",
        subcategories=["concepts", "nodes", "topics", "services", "actions", "launch", "qos", "troubleshooting"],
    )

    domain.add_entry(KnowledgeEntry(
        id="ros2-concepts-001",
        title="ROS2 Core Concepts and Architecture",
        content="""ROS2 is a middleware framework for building distributed robot systems. It provides communication, hardware abstraction, and tooling.

Core concepts:
- Nodes: Individual processes that perform computation
- Topics: Named buses for pub/sub message passing (async)
- Services: Request/reply communication (sync)
- Actions: Long-running tasks with feedback and preemption
- Parameters: Runtime configuration for nodes
- Launch files: Start and configure multiple nodes

Architecture principles:
- DDS (Data Distribution Service) as underlying middleware
- Distributed system — no single point of failure
- Real-time capable (unlike ROS1)
- Multi-platform: Linux, Windows, macOS
- Security built-in (SROS2 with DDS security)

ROS2 distributions:
- Humble Hawksbill (LTS, Ubuntu 22.04)
- Iron Irwini (Ubuntu 23.04)
- Jazzy Jalisco (LTS, Ubuntu 24.04)
- Rolling (continuous development)""",
        domain="ros2",
        category="concepts",
        tags=["ros2", "architecture", "middleware", "dds"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "ros2 run demo_nodes_cpp talker # Run a node",
            "ros2 topic list # List active topics",
            "ros2 node info /talker # Inspect a node",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-nodes-001",
        title="Creating ROS2 Nodes (Python and C++)",
        content="""Nodes are the fundamental units in ROS2 — each node runs in its own process and performs a specific function.

Python node (rclpy):
```python
import rclpy
from rclpy.node import Node

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.get_logger().info('Node started')
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        self.get_logger().info('Timer fired')

def main():
    rclpy.init()
    node = MyNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
```

C++ node (rclcpp):
```cpp
#include <rclcpp/rclcpp.hpp>

class MyNode : public rclcpp::Node {
public:
    MyNode() : Node("my_node") {
        RCLCPP_INFO(this->get_logger(), "Node started");
        timer_ = this->create_wall_timer(
            1s, std::bind(&MyNode::timer_callback, this));
    }
private:
    void timer_callback() {
        RCLCPP_INFO(this->get_logger(), "Timer fired");
    }
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MyNode>());
    rclcpp::shutdown();
    return 0;
}
```""",
        domain="ros2",
        category="nodes",
        tags=["ros2", "nodes", "rclpy", "rclcpp"],
        difficulty=DifficultyLevel.BEGINNER,
        prerequisites=["ros2-concepts-001"],
        examples=[
            "Python: ros2 run my_package my_node",
            "C++: colcon build --packages-select my_package",
            "Debug: ros2 run my_package my_node --ros-args --log-level DEBUG",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-topics-001",
        title="ROS2 Topics — Publisher/Subscriber Communication",
        content="""Topics are the primary communication mechanism in ROS2 — publishers send messages, subscribers receive them asynchronously.

Publisher (Python):
```python
from std_msgs.msg import String

publisher = self.create_publisher(String, 'topic_name', 10)
msg = String()
msg.data = 'Hello ROS2'
publisher.publish(msg)
```

Subscriber (Python):
```python
self.subscription = self.create_subscription(
    String, 'topic_name', self.callback, 10)

def callback(self, msg):
    self.get_logger().info(f'Received: {msg.data}')
```

Common message types:
- std_msgs/String, Int32, Float64, Bool
- sensor_msgs/Image, LaserScan, PointCloud2, Imu, JointState
- geometry_msgs/Twist, Pose, Point, Quaternion, TransformStamped
- nav_msgs/Odometry, Path

QoS (Quality of Service):
- Reliability: RELIABLE vs BEST_EFFORT
- Durability: VOLATILE vs TRANSIENT_LOCAL
- History: KEEP_LAST(n) vs KEEP_ALL
- Must match between publisher and subscriber""",
        domain="ros2",
        category="topics",
        tags=["ros2", "topics", "publisher", "subscriber", "pub/sub"],
        difficulty=DifficultyLevel.BEGINNER,
        prerequisites=["ros2-concepts-001"],
        examples=[
            "ros2 topic echo /cmd_vel # View messages on topic",
            "ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}}' # Publish",
            "ros2 topic hz /scan # Measure message rate",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-services-001",
        title="ROS2 Services — Request/Reply Communication",
        content="""Services provide synchronous request/reply communication — client sends request, waits for server response.

Service definition (.srv file):
```
# Request
int32 a
int32 b
---
# Response
int32 sum
```

Service server (Python):
```python
from example_interfaces.srv import AddTwoInts

self.service = self.create_service(
    AddTwoInts, 'add_two_ints', self.callback)

def callback(self, request, response):
    response.sum = request.a + request.b
    return response
```

Service client (Python):
```python
self.client = self.create_client(AddTwoInts, 'add_two_ints')

async def call_service(self, a, b):
    while not self.client.wait_for_service(timeout_sec=1.0):
        self.get_logger().info('Service not available, waiting...')
    request = AddTwoInts.Request()
    request.a = a
    request.b = b
    future = self.client.call_async(request)
    response = await future
    return response.sum
```

Common service types:
- std_srvs/SetBool, Trigger, Empty
- Custom .srv files in package/srv/ directory""",
        domain="ros2",
        category="services",
        tags=["ros2", "services", "request", "reply", "synchronous"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["ros2-topics-001"],
        examples=[
            "ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts '{a: 5, b: 3}'",
            "ros2 service list # List available services",
            "ros2 interface show example_interfaces/srv/AddTwoInts # View service definition",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-actions-001",
        title="ROS2 Actions — Long-Running Tasks with Feedback",
        content="""Actions are for long-running tasks that need feedback and can be preempted — navigation, grasping, trajectory execution.

Action definition (.action file):
```
# Goal
geometry_msgs/PoseStamped target_pose
---
# Result
float32 distance_traveled
bool success
---
# Feedback
float32 remaining_distance
```

Action server (Python):
```python
from rclpy.action import ActionServer
from nav2_msgs.action import NavigateToPose

self.action_server = ActionServer(
    self, NavigateToPose, 'navigate_to_pose', self.execute_callback)

async def execute_callback(self, goal_handle):
    goal = goal_handle.request
    while not reached:
        if goal_handle.is_cancel_requested:
            goal_handle.canceled()
            return NavigateToPose.Result()
        # Move toward goal
        feedback = NavigateToPose.Feedback()
        feedback.remaining_distance = calc_distance()
        goal_handle.publish_feedback(feedback)
    goal_handle.succeed()
    result = NavigateToPose.Result()
    result.success = True
    return result
```

Action client (Python):
```python
from rclpy.action import ActionClient
self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
goal = NavigateToPose.Goal()
goal.target_pose = target
future = self.action_client.send_goal_async(goal, feedback_callback=self.fb_cb)
```""",
        domain="ros2",
        category="actions",
        tags=["ros2", "actions", "long-running", "feedback", "preempt"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["ros2-services-001"],
        examples=[
            "ros2 action list # List available actions",
            "ros2 action send_goal /navigate nav2_msgs/action/NavigateToPose '{target_pose: ...}'",
            "ros2 action info /navigate # View action status",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-launch-001",
        title="ROS2 Launch Files — Starting Multiple Nodes",
        content="""Launch files start and configure multiple ROS2 nodes simultaneously — essential for complex robot systems.

Python launch file (launch/my_robot.launch.py):
```python
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('speed', default_value='1.0'),

        Node(
            package='my_robot',
            executable='motor_controller',
            name='motor_ctrl',
            parameters=[{'max_speed': LaunchConfiguration('speed')}],
        ),

        Node(
            package='my_robot',
            executable='sensor_driver',
            name='lidar',
            remappings=[('/scan', '/lidar/scan')],
        ),

        Node(
            package='my_robot',
            executable='navigation',
            name='nav',
        ),
    ])
```

Running launch files:
- ros2 launch my_robot my_robot.launch.py
- ros2 launch my_robot my_robot.launch.py speed:=2.0

Include other launch files:
- IncludeLaunchDescription(PythonLaunchDescriptionSource([
    get_package_share_directory('nav2_bringup'), '/launch/nav2.launch.py']))""",
        domain="ros2",
        category="launch",
        tags=["ros2", "launch", "startup", "configuration"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["ros2-nodes-001"],
        examples=[
            "ros2 launch my_package robot.launch.py",
            "ros2 launch my_package robot.launch.py use_sim:=true",
            "ros2 launch --show-args my_package robot.launch.py # Show arguments",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-qos-001",
        title="ROS2 QoS — Quality of Service Profiles",
        content="""QoS (Quality of Service) controls how messages are delivered between publishers and subscribers — mismatched QoS is the #1 cause of 'no messages received' in ROS2.

QoS settings:
- Reliability: RELIABLE (guaranteed delivery) vs BEST_EFFORT (may drop)
- Durability: TRANSIENT_LOCAL (late subscribers get last message) vs VOLATILE (only active subscribers)
- History: KEEP_LAST(n) (buffer n messages) vs KEEP_ALL
- Deadline: Expected interval between messages
- Lifespan: How long messages are valid
- Liveliness: How to detect dead publishers

Common profiles:
- rclpy.qos.qos_profile_sensor_data: BEST_EFFORT, KEEP_LAST(5) — for high-rate sensor data
- rclpy.qos.qos_profile_parameters: RELIABLE, TRANSIENT_LOCAL — for parameters
- rclpy.qos.qos_profile_services_default: RELIABLE for services

Matching rules:
- Publisher and subscriber MUST match on reliability and durability
- BEST_EFFORT publisher + RELIABLE subscriber = NO MESSAGES
- Use qos_profile_sensor_data for camera, LiDAR, IMU""",
        domain="ros2",
        category="qos",
        tags=["ros2", "qos", "quality of service", "reliability"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["ros2-topics-001"],
        examples=[
            "from rclpy.qos import qos_profile_sensor_data; self.create_subscription(LaserScan, '/scan', cb, qos_profile_sensor_data)",
            "ros2 topic info /scan -v # Show QoS profile",
            "Mismatch fix: both pub and sub must use same reliability/durability",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="ros2-troubleshoot-001",
        title="Common ROS2 Errors and Fixes",
        content="""Frequent ROS2 errors and their solutions:

1. Node not receiving messages (QoS mismatch)
   Fix: ros2 topic info /topic -v to check QoS, ensure pub/sub match on reliability and durability

2. 'Package not found' after colcon build
   Fix: source install/setup.bash after every build, check package.xml has correct name

3. Launch file syntax error
   Fix: Ensure generate_launch_description() returns LaunchDescription, check imports

4. Service call hangs forever
   Fix: Check server node is running, verify service name matches, check QoS

5. 'Unknown substitution' in launch file
   Fix: Use LaunchConfiguration('arg_name') not $(var arg_name) (that's ROS1 XML syntax)

6. TF transform not found
   Fix: Check tf2_ros.Buffer and TransformListener are running, verify frame names match exactly

7. colcon build fails with CMake error
   Fix: Check CMakeLists.txt has find_package(rclcpp REQUIRED), ament_target_dependencies()

8. Node crashes with 'rclpy not initialized'
   Fix: Call rclpy.init() before creating any nodes, rclpy.shutdown() at end

9. Parameter not updating
   Fix: Declare parameter with self.declare_parameter('name', default), use self.get_parameter('name').value

10. Action goal rejected
    Fix: Check action server is running, verify goal type matches .action definition""",
        domain="ros2",
        category="troubleshooting",
        tags=["ros2", "errors", "debugging", "troubleshooting"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        examples=[
            "No messages: ros2 topic echo /topic (check QoS with -v flag)",
            "Build fails: source /opt/ros/humble/setup.bash before colcon build",
            "TF error: ros2 run tf2_tools view_frames to visualize TF tree",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created ROS2 domain with {len(domain.entries)} entries")
    return domain
