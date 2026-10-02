"""Industrial Robots — knowledge domain for industrial robot arms and systems."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_industrial_robots_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="industrial_robots",
        description="Industrial robot arms — kinematics, programming, safety, and applications in manufacturing and automation.",
        subcategories=["types", "kinematics", "programming", "safety", "applications", "brands"],
    )

    domain.add_entry(KnowledgeEntry(
        id="indrobot-types-001",
        title="Industrial Robot Types and Configurations",
        content="""Industrial robots are programmable manipulators for automation — different configurations suit different tasks and environments.

Robot Configurations:

1. Articulated (6-Axis)
   - 6 rotary joints (like human arm)
   - Workspace: Spherical (~2m radius typical)
   - Payload: 3-2300 kg
   - Speed: 1-5 m/s
   - Use: Welding, painting, assembly, material handling
   - Pros: Maximum flexibility, complex motions
   - Cons: Singularities, complex control
   - Examples: FANUC M-20, ABB IRB 6700, KUKA KR 60

2. SCARA (Selective Compliance Articulated Robot Arm)
   - 4 axes (3 rotary + 1 linear)
   - Workspace: Cylindrical
   - Payload: 1-50 kg
   - Speed: Very fast (up to 10 m/s)
   - Use: Pick-and-place, assembly, packaging
   - Pros: Fast, rigid in Z, compliant in XY
   - Cons: Limited workspace, can't reach under objects
   - Examples: Epson LS6, Yamaha YK-XG, ABB IRB 910SC

3. Delta (Parallel)
   - 3-4 arms connected to fixed base
   - Workspace: Dome-shaped (limited)
   - Payload: 0.5-8 kg (light)
   - Speed: Extremely fast (up to 15 m/s)
   - Use: High-speed pick-and-place, packaging, food
   - Pros: Very fast, lightweight, clean
   - Cons: Limited payload, small workspace
   - Examples: ABB IRB 360, FANUC M-3, Delta Tau

4. Cartesian (Gantry)
   - 3 linear axes (X, Y, Z)
   - Workspace: Rectangular
   - Payload: 1-1000 kg
   - Speed: Slow to medium (0.5-2 m/s)
   - Use: CNC loading, 3D printing, large part handling
   - Pros: Simple control, high precision, large workspace
   - Cons: Slow, bulky, expensive for large sizes
   - Examples: Custom gantry systems, Bosch Rexroth TS5

5. Collaborative (Cobots)
   - 6-axis, force-limited, safe for human interaction
   - Payload: 3-35 kg
   - Speed: Slow (safety limited, ~1 m/s)
   - Use: Assembly, machine tending, inspection, logistics
   - Pros: No safety fence, easy programming, flexible
   - Cons: Slower than industrial robots, lower payload
   - Examples: Universal Robots UR5e, FANUC CRX-10, ABB GoFa

Robot Specifications:
- DOF (Degrees of Freedom): Number of axes (6 typical)
- Payload: Maximum weight robot can carry (kg)
- Reach: Maximum distance from base to wrist (mm)
- Repeatability: Ability to return to same position (±0.01-0.1mm)
- Accuracy: Ability to reach commanded position (±0.1-1mm)
- Cycle time: Time for standard motion (e.g., 25-200-25mm)""",
        domain="industrial_robots",
        category="types",
        tags=["industrial robots", "articulated", "scara", "delta", "cobot"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "6-axis: FANUC M-20iD/25, 25kg payload, 1831mm reach, ±0.03mm repeatability",
            "SCARA: Epson LS6-702S, 700mm reach, 6kg payload, 0.01mm repeatability",
            "Cobot: Universal Robots UR5e, 5kg payload, 850mm reach, force-limited",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="indrobot-kinematics-001",
        title="Robot Kinematics — Forward and Inverse",
        content="""Robot kinematics describes motion without considering forces — essential for robot control, path planning, and simulation.

Forward Kinematics (FK):
- Input: Joint angles (θ1, θ2, ..., θ6)
- Output: End-effector pose (position + orientation)
- Method: Multiply transformation matrices (DH parameters)
- Use: Given joint encoders, where is the tool?

DH (Denavit-Hartenberg) Parameters:
- a: Link length (distance along x-axis)
- α: Link twist (rotation about x-axis)
- d: Link offset (distance along z-axis)
- θ: Joint angle (rotation about z-axis)

Transformation Matrix (4x4):
```
T = [[R, t],
     [0, 1]]

where R is 3x3 rotation matrix, t is 3x1 translation vector
```

Inverse Kinematics (IK):
- Input: Desired end-effector pose (x, y, z, roll, pitch, yaw)
- Output: Joint angles to reach that pose
- Methods:
  1. Analytical: Closed-form solution (fast, exists for specific geometries)
  2. Numerical: Iterative (Jacobian-based, works for any robot)
  3. Learning-based: Neural network (trained on FK data)
- Use: Given desired tool position, what joint angles needed?

Jacobian Matrix:
- Relates joint velocities to end-effector velocities
- J = ∂x/∂θ (6×6 matrix for 6-DOF robot)
- v = J × q̇ (end-effector velocity = Jacobian × joint velocities)
- Singularities: det(J) = 0 (robot loses DOF, joint velocities → ∞)

IK Solvers:
- IKFast (OpenRAVE): Analytical solver generator (very fast)
- TRAC-IK: Numerical solver with multiple modes (speed, distance, manipulation)
- Bio-IK: Optimization-based (handles redundancy, constraints)
- MoveIt: ROS2 motion planning framework with IK integration

Example (Python with roboticstoolbox):
```python
import roboticstoolbox as rtb

# Load robot model
robot = rtb.models.UR5()

# Forward kinematics
q = [0, -1.57, 0, -1.57, 0, 0]  # joint angles (radians)
T = robot.fkine(q)  # end-effector pose (SE3)
print(T)

# Inverse kinematics
T_target = rtb.SE3(0.5, 0, 0.5)  # desired pose
q_solution = robot.ikine(T_target)
print(q_solution.q)  # joint angles
```""",
        domain="industrial_robots",
        category="kinematics",
        tags=["kinematics", "forward", "inverse", "jacobian", "dh parameters"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["indrobot-types-001"],
        examples=[
            "FK: q = [0, -π/2, 0, -π/2, 0, 0] → T = [[1,0,0,0.5], [0,1,0,0], [0,0,1,0.8], [0,0,0,1]]",
            "IK: T_target = SE3(0.5, 0, 0.5) → q = [0.1, -1.2, 0.8, -0.3, 0.2, 0.5]",
            "Singularity: Joint 5 at 0° → wrist aligned, lose rotation DOF",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="indrobot-programming-001",
        title="Industrial Robot Programming Methods",
        content="""Industrial robots can be programmed in multiple ways — teach pendant, offline, and collaborative methods for different applications.

Programming Methods:

1. Teach Pendant (Online Programming)
   - Operator physically moves robot to desired positions
   - Record points, create program (move to point 1, open gripper, move to point 2, close gripper)
   - Languages: KAREL (FANUC), RAPID (ABB), KRL (KUKA), INFORM (Yaskawa)
   - Pros: Intuitive, no CAD model needed, immediate feedback
   - Cons: Robot downtime during programming, safety risks

2. Offline Programming (OLP)
   - Program in simulation (CAD-based)
   - Transfer program to real robot (calibration required)
   - Software: RoboDK, FANUC ROBOGUIDE, ABB RobotStudio, KUKA.Sim
   - Pros: No production downtime, complex paths, optimization
   - Cons: Requires accurate CAD, calibration errors

3. Lead-Through (Cobots)
   - Operator physically guides robot by hand
   - Robot records trajectory or learns task
   - Pros: Very intuitive, no training needed, safe
   - Cons: Limited precision, slow, repetitive motions only

4. Textual Programming
   - Write code in robot language or Python/C++
   - Use SDK/API (FANUC FANUC.PC, Universal Robots URScript)
   - Pros: Complex logic, integration with external systems
   - Cons: Requires programming knowledge

Common Robot Program Structure:
```
PROGRAM pick_and_place
  ; Approach
  MOVE P[1] 100% FINE   ; Move to approach position
  MOVE L P[2] 500mm/min CNT50  ; Linear move to pick position
  WAIT DI[1]=ON          ; Wait for part present sensor
  
  ; Grasp
  CALL GRIP_OPEN
  WAIT 0.2s
  CALL GRIP_CLOSE
  WAIT DI[2]=ON          ; Wait for grip confirm
  
  ; Transport
  MOVE L P[3] 200mm/min CNT100  ; Lift up
  MOVE J P[4] 100% CNT50        ; Joint move to place approach
  MOVE L P[5] 300mm/min CNT50   ; Linear to place position
  
  ; Release
  CALL GRIP_OPEN
  WAIT 0.2s
  MOVE L P[6] 200mm/min CNT100  ; Lift away
  
  RETURN
END
```

Motion Types:
- Joint (J): Fastest path, joints move independently (non-linear TCP path)
- Linear (L): Straight line in Cartesian space (all joints coordinated)
- Circular (C): Arc motion (defined by 3 points: start, via, end)
- SPLINE: Smooth continuous motion (complex paths)""",
        domain="industrial_robots",
        category="programming",
        tags=["programming", "teach pendant", "offline", "rapid", "karel"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["indrobot-types-001"],
        examples=[
            "Teach pendant: Jog robot to position, record point, add instruction (MOVE, WAIT, DO)",
            "Offline: Import CAD, define TCP, create path in RoboDK, post-process for robot",
            "Lead-through: Guide cobot through task, set speed/force limits, save program",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="indrobot-safety-001",
        title="Robot Safety Standards and Risk Assessment",
        content="""Robot safety protects humans from robot hazards — standards define requirements for design, installation, and operation.

Safety Standards:
- ISO 10218-1/2: Robot safety (manufacturers, integrators, users)
- ISO/TS 15066: Collaborative robot operation (force/pressure limits)
- ANSI/RIA R15.06: North American robot safety standard
- IEC 61508: Functional safety (safety-related control systems)

Risk Assessment Process:
1. Identify hazards: Mechanical (crushing, shearing), electrical, thermal, noise
2. Estimate risk: Severity × probability × exposure
3. Reduce risk: Inherent design, safeguarding, information for use
4. Iterate: Re-assess after each mitigation

Safeguarding Methods:

1. Fixed Barriers (Physical Guards)
   - Enclose robot workspace completely
   - Interlocked gates (robot stops when opened)
   - Material: Polycarbonate, wire mesh, metal panels
   - Height: 2m+ (prevent climbing/ reaching over)

2. Presence-Sensing Devices
   - Light curtains: Infrared beams (break → stop)
   - Laser scanners: 2D area scanning (detect humans in zone)
   - Safety mats: Pressure-sensitive floor mats
   - Cameras: Vision-based human detection

3. Safety-Rated Monitored Stop
   - Robot stops when human enters workspace
   - Resume only after manual reset (safe condition)
   - Use: Teach mode, maintenance

4. Speed and Separation Monitoring
   - Laser scanner creates warning and protective zones
   - Robot slows when human in warning zone
   - Robot stops when human in protective zone
   - Minimum distance: d = (v_robot × t_stop) + d_safe

Collaborative Robot Safety (ISO/TS 15066):
- Quasi-static contact: Slow, sustained contact
  - Head: 65N, Hand: 140N, Body: 210N
- Transient contact: Quick impact
  - Head: 65N, Hand: 140N, Body: 210N
- Pain thresholds: Vary by body part (see ISO/TS 15066 Table A.2)
- Speed limits: 250mm/s typical (reduces to 150mm/s for head/neck)

Safety Functions:
- Safe Torque Off (STO): Remove power from motors (highest safety level)
- Safe Stop 1 (SS1): Controlled stop, then STO
- Safe Stop 2 (SS2): Controlled stop, maintain position (powered)
- Safely Limited Speed (SLS): Limit speed to safe value
- Safely Limited Force (SLF): Limit force/torque (cobots)""",
        domain="industrial_robots",
        category="safety",
        tags=["safety", "iso 10218", "risk assessment", "light curtain", "cobot"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["indrobot-types-001"],
        examples=[
            "Light curtain: SICK C4000, Category 4, PLe, 14mm resolution",
            "Laser scanner: SICK microScan3, 275° field, 5m range, 70ms response",
            "Cobot force limit: 150N hand, 210N body (ISO/TS 15066 quasi-static)",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Industrial Robots domain with {len(domain.entries)} entries")
    return domain
