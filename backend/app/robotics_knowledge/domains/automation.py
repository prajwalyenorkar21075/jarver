"""Automation — knowledge domain for industrial automation and systems integration."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_automation_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="automation",
        description="Industrial automation — system integration, Industry 4.0, IoT, manufacturing execution, and process optimization.",
        subcategories=["basics", "integration", "industry4", "iot", "manufacturing", "optimization"],
    )

    domain.add_entry(KnowledgeEntry(
        id="automation-basics-001",
        title="Industrial Automation Fundamentals",
        content="""Industrial automation uses control systems (PLCs, robots, HMI) to operate equipment with minimal human intervention — improving productivity, quality, and safety.

Automation Pyramid (ISA-95):
- Level 4: ERP (Enterprise Resource Planning) — Business systems (SAP, Oracle)
- Level 3: MES (Manufacturing Execution System) — Production tracking, scheduling
- Level 2: SCADA/HMI — Supervisory control, data acquisition, visualization
- Level 1: PLC/DCS — Direct process control, logic, sequencing
- Level 0: Sensors/Actuators — Physical process measurement and control

Automation Types:

1. Fixed Automation (Hard Automation)
   - Dedicated equipment for high-volume production
   - Examples: Assembly lines, transfer machines, CNC machining centers
   - Pros: High speed, low cost per unit, consistent quality
   - Cons: Inflexible, expensive to change, long setup time
   - Use: Automotive, consumer electronics, packaging

2. Programmable Automation
   - Equipment can be reprogrammed for different products
   - Examples: Industrial robots, CNC machines, PLC-controlled systems
   - Pros: Flexible, batch production (10-1000 units)
   - Cons: Slower than fixed, programming time, lower speed
   - Use: Aerospace, job shops, custom manufacturing

3. Flexible Automation
   - Quick changeover between products (automatic)
   - Examples: FMS (Flexible Manufacturing Systems), AGV systems
   - Pros: High variety, low downtime, automated changeover
   - Cons: Expensive, complex, requires skilled maintenance
   - Use: High-mix low-volume (HMLV) manufacturing

Automation Benefits:
- Productivity: 24/7 operation, faster cycle times
- Quality: Consistent, repeatable, reduced variation
- Safety: Remove humans from dangerous tasks
- Cost: Lower labor cost, reduced waste, less rework
- Flexibility: Quick product changeovers (programmable/flexible)

Automation Challenges:
- High initial investment (ROI 2-5 years typical)
- Requires skilled workforce (programming, maintenance)
- Integration complexity (multi-vendor systems)
- Cybersecurity risks (connected systems)
- Change management (worker resistance, training)""",
        domain="automation",
        category="basics",
        tags=["automation", "isa-95", "pyramid", "fixed", "programmable", "flexible"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Fixed: Automotive assembly line, 60 jobs/hour, dedicated to one model",
            "Programmable: Robot welding cell, reprogram for different car models",
            "Flexible: FMS with AGVs, machine cells, automated storage — any part in any order",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="automation-integration-001",
        title="System Integration — Connecting Automation Components",
        content="""System integration connects disparate automation components (PLCs, robots, vision, MES) into a cohesive system — communication protocols and data flow are critical.

Integration Layers:

1. Field Level (Sensors/Actuators)
   - Protocols: IO-Link, AS-Interface, HART
   - Data: Process variables (temperature, pressure, position)
   - Update rate: 1-100ms
   - Distance: <100m (field bus)

2. Control Level (PLCs, Robots)
   - Protocols: EtherNet/IP, PROFINET, EtherCAT, Modbus TCP
   - Data: Control commands, setpoints, status
   - Update rate: 1-10ms
   - Distance: <1km (industrial Ethernet)

3. Supervisory Level (SCADA, HMI)
   - Protocols: OPC UA, MQTT, REST API
   - Data: Alarms, trends, recipes, operator commands
   - Update rate: 100ms-1s
   - Distance: Site-wide (LAN)

4. Enterprise Level (MES, ERP)
   - Protocols: REST API, SOAP, database integration
   - Data: Orders, inventory, quality, scheduling
   - Update rate: 1s-1min
   - Distance: Global (WAN, cloud)

Integration Challenges:

1. Multi-Vendor Interoperability
   - Problem: Different vendors use different protocols
   - Solution: OPC UA (universal translation), gateway devices
   - Example: Allen-Bradley PLC → OPC UA → Siemens Robot

2. Data Modeling
   - Problem: Inconsistent naming, units, data structures
   - Solution: Unified namespace (UNS), ISA-95 object model
   - Example: All temperatures in °C, all pressures in bar

3. Real-Time Requirements
   - Problem: Motion control needs <1ms, MES can tolerate 1s
   - Solution: Network segmentation, QoS, time-sensitive networking (TSN)
   - Example: Separate VLAN for motion control vs. data collection

4. Security
   - Problem: Connected systems vulnerable to cyber attacks
   - Solution: Network segmentation, firewalls, authentication, encryption
   - Example: DMZ between OT and IT networks, OPC UA with certificates

Integration Architecture Patterns:

1. Hub-and-Spoke (Centralized)
   - Central server (OPC UA server, MQTT broker)
   - All devices connect to central hub
   - Pros: Simple, centralized management
   - Cons: Single point of failure, scalability limits

2. Peer-to-Peer (Distributed)
   - Devices communicate directly
   - No central server required
   - Pros: Robust, scalable
   - Cons: Complex configuration, harder to manage

3. Publish-Subscribe
   - Publishers send data to topics
   - Subscribers receive data from topics
   - Decoupled: Publishers don't know subscribers
   - Pros: Flexible, scalable, real-time
   - Use: MQTT, OPC UA pub/sub, DDS""",
        domain="automation",
        category="integration",
        tags=["integration", "opc ua", "mqtt", "protocols", "isa-95"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["automation-basics-001"],
        examples=[
            "OPC UA: Universal interface — PLC publishes data, MES subscribes",
            "MQTT: Lightweight pub/sub — sensors publish, cloud subscribes",
            "Gateway: Modbus TCP → OPC UA — translate legacy protocols",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="automation-industry4-001",
        title="Industry 4.0 and Smart Manufacturing",
        content="""Industry 4.0 is the digital transformation of manufacturing — IoT, cloud computing, AI, and cyber-physical systems create smart factories.

Industry 4.0 Pillars:

1. Interoperability
   - Machines, devices, sensors, people connect via IIoT (Industrial IoT)
   - Standards: OPC UA, MQTT, UMATI (for machine tools)
   - Challenge: Legacy equipment (retrofit with sensors/gateways)

2. Information Transparency
   - Digital twin: Virtual copy of physical system
   - Context: Sensor data + location + time + recipe
   - Use: Simulation, optimization, predictive maintenance

3. Technical Assistance
   - AI/ML: Analyze data, support decision-making
   - AR/VR: Visualize data, remote assistance
   - Cobots: Physical assistance, collaborative work

4. Decentralized Decisions
   - Cyber-physical systems make decisions autonomously
   - Edge computing: Process data locally (low latency)
   - Exception handling: Escalate to humans for unusual cases

Key Technologies:

1. Industrial IoT (IIoT)
   - Smart sensors: Embedded computing, communication
   - Connectivity: 5G, WiFi 6, LoRaWAN, NB-IoT
   - Platforms: AWS IoT, Azure IoT, MindSphere (Siemens)
   - Data: Time-series databases (InfluxDB, TimescaleDB)

2. Cloud Computing
   - IaaS: Infrastructure (AWS EC2, Azure VMs)
   - PaaS: Platform (AWS IoT, Azure IoT Hub)
   - SaaS: Software (Manufacturing apps, analytics)
   - Hybrid: On-premise + cloud (sensitive data on-prem)

3. Big Data Analytics
   - Volume: TB-PB of sensor data
   - Velocity: Real-time streaming (Kafka, Spark Streaming)
   - Variety: Structured (SQL), unstructured (images, logs)
   - Tools: Hadoop, Spark, Python (Pandas, Dask)

4. Artificial Intelligence
   - Predictive maintenance: Predict failures before they occur
   - Quality inspection: Computer vision for defect detection
   - Process optimization: Reinforcement learning for control
   - Digital twin: Simulation + ML for what-if analysis

5. Additive Manufacturing (3D Printing)
   - Prototyping: Rapid iteration, complex geometries
   - Production: Custom parts, spare parts on-demand
   - Materials: Plastics, metals, ceramics, composites
   - Technologies: FDM, SLA, SLS, DMLS (metal)

Implementation Roadmap:
1. Assess: Current state, gaps, opportunities
2. Strategy: Business case, ROI, priorities
3. Pilot: Start small (one line, one use case)
4. Scale: Expand successful pilots
5. Transform: Full digital integration""",
        domain="automation",
        category="industry4",
        tags=["industry 4.0", "iiot", "smart manufacturing", "digital twin", "cloud"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["automation-basics-001", "automation-integration-001"],
        examples=[
            "Digital twin: Simulate production line, optimize scheduling, predict bottlenecks",
            "Predictive maintenance: Vibration sensor + ML → predict bearing failure 2 weeks ahead",
            "IIoT platform: MQTT sensors → AWS IoT Core → Lambda → S3 → QuickSight dashboard",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="automation-optimization-001",
        title="Process Optimization and Continuous Improvement",
        content="""Process optimization improves manufacturing performance — OEE (Overall Equipment Effectiveness), cycle time reduction, and quality improvement through data-driven methods.

Key Metrics:

1. OEE (Overall Equipment Effectiveness)
   - OEE = Availability × Performance × Quality
   - Availability: Run time / Planned time (downtime losses)
   - Performance: Actual speed / Ideal speed (speed losses)
   - Quality: Good parts / Total parts (quality losses)
   - World-class: 85%+ OEE
   - Typical: 60% OEE (lots of improvement potential)

2. Cycle Time
   - Time to produce one part (from start to finish)
   - Takt time: Customer demand rate (available time / customer demand)
   - Target: Cycle time ≤ Takt time
   - Bottleneck: Slowest process (limits overall throughput)

3. First Pass Yield (FPY)
   - Percentage of parts that pass quality first time (no rework)
   - FPY = (Total parts - Defects) / Total parts × 100%
   - Rolled throughput yield: FPY of entire process (multiply FPY of each step)

Optimization Methods:

1. Lean Manufacturing
   - Identify waste: Defects, overproduction, waiting, non-utilized talent, transportation, inventory, motion, extra-processing (DOWNTIME)
   - Tools: 5S (Sort, Set in order, Shine, Standardize, Sustain), Value stream mapping, Kanban, Kaizen
   - Goal: Maximize value, minimize waste

2. Six Sigma
   - DMAIC: Define, Measure, Analyze, Improve, Control
   - Statistical tools: Control charts, capability analysis, hypothesis testing
   - Goal: Reduce variation, 3.4 defects per million opportunities (6σ)

3. Total Productive Maintenance (TPM)
   - Autonomous maintenance: Operators perform basic maintenance
   - Planned maintenance: Scheduled preventive maintenance
   - Goal: Zero breakdowns, zero defects, zero accidents

4. Data-Driven Optimization
   - Collect: Sensor data, production data, quality data
   - Analyze: Identify correlations, root causes, opportunities
   - Implement: Process changes, parameter adjustments
   - Monitor: Track KPIs, verify improvement
   - Tools: Python (Pandas, Scikit-learn), Minitab, JMP

Example Optimization Project:
```python
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Load production data
df = pd.read_csv('production_data.csv')
# Columns: timestamp, temperature, pressure, speed, quality_score

# Feature engineering
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
df['shift'] = df['hour'].apply(lambda h: 'day' if 6<=h<18 else 'night')

# Train model to predict quality
X = df[['temperature', 'pressure', 'speed', 'hour']]
y = df['quality_score']
model = RandomForestRegressor(n_estimators=100)
model.fit(X, y)

# Feature importance
importances = model.feature_importances_
print(f"Temperature: {importances[0]:.2%}")
print(f"Pressure: {importances[1]:.2%}")
print(f"Speed: {importances[2]:.2%}")

# Optimize: Find parameter settings that maximize quality
from scipy.optimize import minimize
def objective(params):
    pred = model.predict([params])[0]
    return -pred  # minimize negative = maximize quality

result = minimize(objective, x0=[20, 5, 100], bounds=[(15,25), (3,7), (80,120)])
print(f"Optimal: temp={result.x[0]:.1f}, pressure={result.x[1]:.1f}, speed={result.x[2]:.1f}")
```""",
        domain="automation",
        category="optimization",
        tags=["optimization", "oee", "lean", "six sigma", "continuous improvement"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["automation-basics-001"],
        examples=[
            "OEE: Availability 90% × Performance 85% × Quality 95% = 72.7% OEE",
            "Bottleneck: Station 3 slowest (45s cycle) → line limited to 80 parts/hour",
            "Data-driven: Random forest model → temperature most important for quality → optimize temp profile",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Automation domain with {len(domain.entries)} entries")
    return domain
