"""HMI/SCADA — knowledge domain."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_hmi_scada_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="hmi_scada",
        description="HMI (Human-Machine Interface) and SCADA (Supervisory Control and Data Acquisition) — operator interfaces for industrial automation and process monitoring.",
        subcategories=["hmi_basics", "scada", "screens", "alarms", "trends", "security", "best_practices"],
    )

    domain.add_entry(KnowledgeEntry(
        id="hmi-basics-001",
        title="HMI Basics and Design Principles",
        content="""HMIs are operator interfaces for monitoring and controlling industrial processes — touchscreens, panels, or PC-based systems.

HMI Types:
- Dedicated HMI panels (7" to 15" touchscreens) — Allen-Bradley, Siemens, Weintek
- PC-based HMI — FactoryTalk View, WinCC, Ignition
- Web-based HMI — Modern, accessible from any browser
- Mobile HMI — Tablets, smartphones for remote monitoring

Design Principles (ISA-101):
1. Grayscale background — Color for information, not decoration
2. High-performance graphics — Minimal clutter, clear information hierarchy
3. Gray background (210-225 brightness) — Reduces eye strain
4. Color meaning: Red=alarm/danger, Yellow=warning, Green=safe/running, Blue=informational
5. Consistent navigation — Same layout across all screens
6. Pop-up details — Overview → detail drill-down pattern

Screen Hierarchy:
- Level 1: Plant overview (entire facility)
- Level 2: Area overview (production line, process unit)
- Level 3: Equipment detail (machine, vessel, robot)
- Level 4: Diagnostics/parameter screens

Navigation:
- Persistent menu bar (home, alarms, trends, help)
- Breadcrumb trail for navigation context
- Faceplate pop-ups for equipment control
- Full-screen takeover only for critical alarms""",
        domain="hmi_scada",
        category="hmi_basics",
        tags=["hmi", "interface", "operator", "design", "isa-101"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Use gray background (#D3D3D3), not bright colors",
            "Red = alarm/fault, Green = running/OK, Yellow = warning/caution",
            "Overview screen shows entire plant, click area to drill down",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="scada-001",
        title="SCADA Systems Architecture",
        content="""SCADA systems provide centralized monitoring and control for distributed industrial processes — water treatment, power grids, oil & gas, manufacturing.

SCADA Architecture:
1. Field Devices — Sensors, actuators, PLCs, RTUs (Remote Terminal Units)
2. Communication Network — Ethernet, fiber, radio, cellular
3. SCADA Servers — Data acquisition, historian, alarm server
4. HMI Clients — Operator workstations, web clients, mobile apps
5. Engineering Workstation — Configuration, programming, maintenance

SCADA Software:
- Ignition (Inductive Automation) — Modern, web-based, SQL historian
- FactoryTalk View SE (Rockwell) — Enterprise-level, ActiveDirectory integration
- WinCC (Siemens) — TIA Portal integration, scalable
- Wonderware InTouch/AVEVA — Legacy but widely installed
- openSCADA — Open source, Linux-based

Key Functions:
- Real-time data acquisition (1-10 second updates typical)
- Alarm management (priority, shelving, acknowledgment)
- Historical data logging (trend analysis, reporting)
- Recipe management (product changeovers)
- User authentication and audit trails
- Redundancy (hot standby servers)

Communication:
- OPC UA for multi-vendor integration
- Modbus TCP for simple devices
- DNP3 for utilities (electric, water)
- MQTT for IIoT/cloud integration""",
        domain="hmi_scada",
        category="scada",
        tags=["scada", "architecture", "monitoring", "control"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["hmi-basics-001"],
        examples=[
            "Ignition: Tag-based architecture, SQL historian, Perspective web HMI",
            "FactoryTalk: Linear tag database, VBA scripting, FactoryTalk ViewSE",
            "Redundancy: Primary/standby servers, automatic failover on failure",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="hmi-screens-001",
        title="HMI Screen Design and Navigation",
        content="""Effective HMI screens follow industry standards (ISA-101, ASM) to reduce operator errors and improve situational awareness.

Screen Types:

1. Overview Screen
   - Shows entire plant/process area
   - Grayscale equipment outlines
   - Color-coded status (green=running, red=fault, yellow=warning)
   - Clickable areas to drill down
   - Key performance indicators (OEE, throughput, quality)

2. Detail Screen
   - Single equipment item (pump, motor, robot)
   - All operating parameters visible
   - Control buttons (start/stop, speed setpoint)
   - Status indicators with color coding
   - Alarm banner at top

3. Alarm Summary Screen
   - Active alarms sorted by priority/time
   - Acknowledge button for each alarm
   - Filter by priority, area, equipment
   - Alarm history with timestamps

4. Trend Screen
   - Real-time and historical data plots
   - Multiple variables on same chart
   - Zoom/pan for detailed analysis
   - Export to CSV/Excel for reporting

Navigation Patterns:
- Persistent header: Area name, navigation buttons, alarm count, user info
- Breadcrumb: Plant > Line 1 > Robot 3 > Servo 4
- Faceplate: Pop-up with equipment controls (appears on click)
- Tabbed interface: Multiple views for complex equipment

Best Practices:
- Max 5-7 clickable items per screen (cognitive load)
- Use animation sparingly (flashing only for critical alarms)
- Consistent colors across all screens
- Provide help text / tooltips for operators""",
        domain="hmi_scada",
        category="screens",
        tags=["hmi", "screens", "design", "navigation", "isa-101"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["hmi-basics-001"],
        examples=[
            "Overview: Gray equipment, green=running, red=fault, yellow=warning",
            "Detail: All parameters visible, start/stop buttons, alarm banner",
            "Trend: Plot temperature, pressure, flow on same chart with different colors",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="hmi-alarms-001",
        title="Alarm Management and Prioritization",
        content="""Alarm management is critical for operator safety and process reliability — poor alarm design leads to alarm floods and missed critical events.

Alarm Priorities (ISA-18.2):
1. Critical (Red) — Immediate action required, safety/environmental risk
2. High (Red/Orange) — Action needed within minutes, equipment damage risk
3. Medium (Yellow) — Action needed within 30 minutes, process upset
4. Low (Blue) — Operator awareness, no immediate action

Alarm Attributes:
- Tag name and description
- Alarm message (clear, actionable text)
- Priority and category
- Setpoint (threshold value)
- Deadband (hysteresis to prevent chatter)
- Delay (time before alarm triggers)
- Shelving/suppression rules

Alarm Rationalization:
- Review every alarm for necessity and priority
- Remove nuisance alarms (fix root cause or delete)
- Target: < 6 alarms per operator per hour (ISA-101)
- Document alarm: cause, consequences, corrective action

Alarm Display:
- Banner at top of screen (red for critical, yellow for warning)
- Alarm summary screen with filtering
- Audible alerts for critical/high alarms only
- Color + text + sound for redundancy
- Acknowledge button (silences audible, alarm stays until cleared)

Common Alarm Mistakes:
- Too many alarms (>100 per hour = alarm flood)
- No priority differentiation (everything is "critical")
- Missing deadband (alarm chatters on/off)
- Unclear alarm messages ("Fault 47" instead of "Motor 1 Overload")""",
        domain="hmi_scada",
        category="alarms",
        tags=["hmi", "alarms", "isa-18.2", "alarm management", "prioritization"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["hmi-basics-001"],
        examples=[
            "Priority: Critical=safety, High=equipment damage, Medium=process upset, Low=info",
            "Deadband: Setpoint=100, deadband=2% → alarm at 100, clears at 98",
            "Delay: Temperature > 100 for 5 seconds → prevents nuisance alarms on startup",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="hmi-trends-001",
        title="Historical Trends and Data Logging",
        content="""Historical trends record process data over time — used for troubleshooting, optimization, regulatory compliance, and performance analysis.

Trend Types:
1. Real-time trends — Live data, last 1-24 hours, for operator monitoring
2. Historical trends — Days/weeks/months of data, for analysis and reporting
3. Event logs — Discrete events (alarms, operator actions, state changes)

Data Logging Configuration:
- Tag selection: Log only necessary tags (reduces storage)
- Sample rate: 1s for critical, 10s for normal, 60s for slow processes
- Storage: SQL database (Ignition), proprietary historian (OSIsoft PI), CSV files
- Retention: 30 days typical, 1 year for regulatory, archive older data

Trend Display:
- X-axis: Time (auto-scale or fixed window)
- Y-axis: Variable values (auto-scale or fixed range)
- Multiple variables: Different colors, legend with units
- Zoom/pan: Mouse wheel to zoom, drag to pan
- Cursors: Show exact values at specific time

Analysis Features:
- Statistics: Min, max, average, standard deviation
- Export: CSV, Excel, PDF reports
- Annotations: Mark events, add notes to trends
- Calculated tags: Efficiency, OEE, cycle time

Common Use Cases:
- Troubleshoot batch failures (compare good vs bad batches)
- Optimize process parameters (find optimal temperature/pressure)
- Regulatory compliance (prove process stayed within limits)
- Predictive maintenance (track vibration, temperature trends)""",
        domain="hmi_scada",
        category="trends",
        tags=["hmi", "trends", "historical", "data logging", "analysis"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["hmi-basics-001"],
        examples=[
            "Log every 1s: temperature, pressure, flow for critical process",
            "Historical: Plot last 7 days of oven temperature to find drift",
            "Export: CSV export for monthly quality report",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="hmi-security-001",
        title="HMI/SCADA Security Best Practices",
        content="""HMI/SCADA security protects industrial processes from cyber threats — unauthorized access, malware, and sabotage can cause safety incidents and production losses.

Security Layers (Defense in Depth):
1. Network segmentation — Separate OT network from IT/enterprise network
2. Firewalls — Control traffic between networks, block unauthorized access
3. Authentication — User accounts, passwords, role-based access control
4. Authorization — Limit what each user role can do (view, operate, configure)
5. Audit trails — Log all operator actions and system events
6. Patch management — Keep HMI/SCADA software and OS updated
7. Physical security — Lock panels, restrict access to control rooms

User Roles:
- Viewer — Read-only access, no control capability
- Operator — Start/stop equipment, acknowledge alarms, adjust setpoints
- Supervisor — Override controls, modify recipes, manage alarms
- Engineer — Configure system, add tags, modify screens
- Administrator — User management, security settings, backups

Authentication:
- Unique user accounts (no shared passwords)
- Strong password policy (length, complexity, expiration)
- Multi-factor authentication for remote access
- Automatic logout after inactivity (15-30 minutes)
- ActiveDirectory/LDAP integration for enterprise systems

Network Security:
- DMZ between IT and OT networks
- No direct internet connection to HMI/SCADA servers
- VPN for remote access (not RDP directly)
- Disable unused services (USB, CD-ROM, wireless)
- Regular vulnerability scans and penetration testing

Common Threats:
- Ransomware (encrypts HMI/SCADA systems)
- Stuxnet-style attacks (modify PLC programs)
- Credential theft (unauthorized remote access)
- USB malware (infected maintenance laptops)""",
        domain="hmi_scada",
        category="security",
        tags=["hmi", "scada", "security", "authentication", "network"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["hmi-basics-001"],
        examples=[
            "Roles: Viewer (read-only), Operator (control), Engineer (configure), Admin (manage)",
            "Network: OT network separate from IT, firewall between, no direct internet",
            "Audit: Log all start/stop commands, setpoint changes, alarm acknowledgments",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created HMI/SCADA domain with {len(domain.entries)} entries")
    return domain
