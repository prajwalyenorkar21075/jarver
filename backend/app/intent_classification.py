"""Voice command intent classification for JARVIS.

Phase 3 Enhancement: Classifies user voice commands into semantic intents
to enable faster routing and more accurate response generation. Supports
multi-intent detection and confidence scoring.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("jarvis.intent")


class Intent(Enum):
    """Voice command intent categories."""
    CODE_GENERATION = "code_generation"
    CODE_EDITING = "code_editing"
    CODE_EXPLANATION = "code_explanation"
    FILE_OPERATION = "file_operation"
    SYSTEM_CONTROL = "system_control"
    INFORMATION_QUERY = "information_query"
    TASK_AUTOMATION = "task_automation"
    NAVIGATION = "navigation"
    MEDIA_CONTROL = "media_control"
    CONVERSATION = "conversation"
    VEDIC_KNOWLEDGE = "vedic_knowledge"
    CAD_MODELING = "cad_modeling"
    ETHICAL_HACKING = "ethical_hacking"
    CYBERSECURITY = "cybersecurity"
    INDUSTRIAL = "industrial"
    PLC = "plc"
    MAINTENANCE = "maintenance"
    CELL_INSPECTION = "cell_inspection"
    VISION = "vision"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Intent classification result with confidence."""
    intent: Intent
    confidence: float
    primary_intent: Intent
    secondary_intent: Optional[Intent]
    entities: dict[str, any]
    is_multi_intent: bool


INTENT_PATTERNS = {
    Intent.CODE_GENERATION: [
        r"\b(create|generate|write|build|make|implement|code|program)\b.*\b(function|class|module|script|program|code|file)\b",
        r"\b(write|create|generate)\b.*\b(in|using|with)\b.*\b(python|javascript|java|cpp|rust|go|typescript)\b",
        r"\b(code|program|script)\b.*\b(that|which|to)\b.*\b(does|can|will)\b",
        r"\b(create|make|build)\b.*\b(a|an|the)?\b.*\b(function|class|component|module)\b",
        r"\b(implement|develop|design)\b.*\b(algorithm|feature|system|api)\b",
    ],
    Intent.CODE_EDITING: [
        r"\b(edit|modify|change|update|fix|refactor|debug|optimize)\b.*\b(code|file|function|class|module)\b",
        r"\b(fix|debug|repair|resolve)\b.*\b(bug|error|issue|problem|crash)\b",
        r"\b(refactor|optimize|improve|clean)\b.*\b(code|function|class|module)\b",
        r"\b(add|remove|delete|insert)\b.*\b(line|code|function|parameter)\b",
        r"\b(rename|replace|substitute)\b.*\b(variable|function|class|file)\b",
    ],
    Intent.CODE_EXPLANATION: [
        r"\b(explain|describe|what|how)\b.*\b(does|is|are|works|work)\b.*\b(code|function|class|this|that)\b",
        r"\b(what|how)\b.*\b(does|is)\b.*\b(this|that|it)\b.*\b(do|does|work|mean)\b",
        r"\b(explain|describe|tell)\b.*\b(me|us)?\b.*\b(about|how|what)\b",
        r"\b(why|how)\b.*\b(does|is|are)\b.*\b(this|that|it)\b",
        r"\b(understand|comprehend)\b.*\b(code|function|logic|algorithm)\b",
    ],
    Intent.FILE_OPERATION: [
        r"\b(open|close|read|write|create|delete|rename|move|copy|save)\b.*\b(file|folder|directory|document)\b",
        r"\b(list|show|find|search|locate)\b.*\b(files|folders|directories)\b",
        r"\b(create|make|new)\b.*\b(folder|directory|file)\b",
        r"\b(delete|remove|erase)\b.*\b(file|folder)\b",
        r"\b(save|export|import)\b.*\b(file|data|document)\b",
    ],
    Intent.SYSTEM_CONTROL: [
        r"\b(open|launch|start|run|execute)\b.*\b(app|application|program|software|youtube|browser|notepad|calculator|chrome|spotify|music)\b",
        r"\b(open|launch)\b.*\b(youtube|gmail|maps|drive|calendar)\b",
        r"\b(close|quit|exit|stop|kill|terminate)\b.*\b(app|application|program|process)\b",
        r"\b(shutdown|restart|reboot|sleep|hibernate)\b.*\b(system|computer|pc|machine)\b",
        r"\b(volume|brightness|screen|display|wifi|bluetooth)\b.*\b(up|down|on|off|increase|decrease)\b",
        r"\b(take|make|create)\b.*\b(screenshot|screencast|recording)\b",
    ],
    Intent.INFORMATION_QUERY: [
        r"\b(what|who|where|when|why|how)\b.*\b(is|are|does|do|can|will|would|should)\b",
        r"\b(search|find|look|google)\b.*\b(for|about)?\b",
        r"\b(tell|show)\b.*\b(me|us)?\b.*\b(about|information|info|details)\b",
        r"\b(define|meaning|definition)\b.*\b(of|for)\b",
        r"\b(weather|time|date|news|stock|price)\b",
    ],
    Intent.TASK_AUTOMATION: [
        r"\b(automate|schedule|remind|alert|notify)\b",
        r"\b(run|execute|perform)\b.*\b(task|job|operation|action)\b",
        r"\b(set|create|add)\b.*\b(timer|reminder|alarm|schedule)\b",
        r"\b(batch|bulk|mass)\b.*\b(process|execute|run)\b",
        r"\b(automatically|auto)\b.*\b(do|run|execute|perform)\b",
    ],
    Intent.NAVIGATION: [
        r"\b(go|navigate|open|jump|switch)\b.*\b(to|in|on)\b",
        r"\b(back|forward|previous|next)\b",
        r"\b(scroll|page|tab|window)\b.*\b(up|down|left|right)\b",
        r"\b(zoom|in|out|fullscreen)\b",
        r"\b(home|dashboard|main|root)\b",
    ],
    Intent.MEDIA_CONTROL: [
        r"\b(play|pause|stop|resume|skip|rewind|fast\s?forward)\b.*\b(music|video|audio|song|movie|show)\b",
        r"\b(next|previous|forward|back)\b.*\b(track|song|episode|chapter)\b",
        r"\b(volume|sound|audio)\b.*\b(up|down|mute|unmute|louder|quieter)\b",
        r"\b(shuffle|repeat|loop)\b",
    ],
    Intent.CONVERSATION: [
        r"\b(hello|hi|hey|greetings|good\s?(morning|afternoon|evening))\b",
        r"\b(how\s+are\s+you|what'?s?\s+up|how'?s\s+it\s+going|how\s+are\s+things|are\s+you\s+there)\b",
        r"\b(thank\s*you|thanks|appreciate)\b",
        r"\b(bye|goodbye|see\s+you|later)\b",
        r"\b(yes|no|maybe|perhaps|sure|ok|okay)\b",
    ],
    Intent.VEDIC_KNOWLEDGE: [
        r"\b(what is|what are|explain|tell me about|describe)\b.*\b(atman|brahman|dharma|karma|moksha|yoga|jnana|bhakti|upanishad|vedas?|gita|bhagavad|ramayana|mahabharata|purana|vedanga|shiksha|kalpa|vyakarana|nirukta|chandas|jyotisha|aranyaka|brahmana)\b",
        r"\b(atman|brahman|dharma|karma|moksha|yoga|jnana|bhakti|upanishad|vedas?|gita|bhagavad|ramayana|mahabharata|purana|vedanga)\b.*\b(meaning|definition|explain|concept|philosophy)\b",
        r"\b(उपनिषद|आत्मा|आत्मन्|ब्रह्म|धर्म|कर्म|मोक्ष|योग|ज्ञान|भक्ति|गीता|रामायण|महाभारत|पुराण|वेद|वेदाङ्ग)\b",
        r"\b(आत्मा म्हणजे|ब्रह्म काय|धर्म काय|गीता मधे|उपनिषदात|रामायणात|महाभारतात)\b",
        r"\b(आत्मा क्या है|ब्रह्म क्या है|गीता में|उपनिषद में|रामायण में|महाभारत में)\b",
        r"\b(compare|difference|relationship|connection)\b.*\b(upanishad|gita|vedas?|atman|brahman|dharma)\b",
        r"\b(vedic|vedanta|shruti|smriti|itihasa|purana)\b.*\b(explain|what|concept|philosophy)\b",
        # Transliterated Marathi/Hindi patterns
        r"\b(atman|aatman|atma)\b.*\b(mhanje|matlab|kya|hai|meaning|kay)\b",
        r"\b(brahman|brahma)\b.*\b(mhanje|matlab|kya|hai|meaning|kay)\b",
        r"\b(gita|geeta)\b.*\b(madhla|madhye|mein|in|chapter|adhyay)\b",
        r"\b(karma|jnana|bhakti)\b.*\b(yoga|yog)\b",
        r"\b(upanishad|upanishads)\b.*\b(ani|aur|and)\b.*\b(gita|geeta)\b",
        r"\b(mahabharat|mahabharata)\b.*\b(madhla|madhye|mein|in)\b.*\b(gita|geeta)\b",
        r"\b(vedanga|vedangas)\b.*\b(ka|ki|ke)\b.*\b(important|mahatva|importance)\b",
        r"\b(vedangas?|vedanga)\b.*\b(important|importance|mahatva|why)\b",
    ],
    Intent.CAD_MODELING: [
        r"\b(create|make|build|add)\b.*\b(box|cube|cylinder|sphere|cone|torus|primitive)\b",
        r"\b(extrude|revolve|cut|union|fillet|chamfer|shell)\b",
        r"\b(sketch|draw|circle|line|arc|rectangle)\b",
        r"\b(cad|3d|model|design)\b.*\b(create|make|build)\b",
        r"\b(measure|volume|area|dimension)\b.*\b(feature|part|body)\b",
        r"\b(import|export)\b.*\b(stl|step|obj|brep|cad)\b",
        r"\b(open|show|display)\b.*\b(cad|3d|viewport|model)\b",
    ],
    Intent.ETHICAL_HACKING: [
        # English patterns - offensive/authorized testing only
        r"\b(pentest|penetration\s*test|ethical\s*hack(?:ing)?|red\s*team)\b",
        r"\b(run|start|execute|perform)\b.*\b(pentest|penetration\s*test|ethical\s*hack)\b",
        r"\b(exploit|exploit\s*validation|exploit\s*analysis)\b",
        r"\b(port\s*scan)\b.*\b(target|host|server)\b",
        r"\b(web|api)\b.*\b(pentest|penetration\s*test)\b",
        r"\b(generate|create)\b.*\b(pentest|penetration\s*test)\b.*\b(report)\b",
        # Hindi patterns
        r"\b(ethical\s*hacking|pentest)\b.*\b(करें|करना|चाहिए)\b",
        r"\b(पेनेट्रेशन\s*टेस्ट|एथिकल\s*हैकिंग)\b",
        # Marathi patterns
        r"\b(ethical\s*hacking|pentest)\b.*\b(करा|करायचे|पाहिजे)\b",
        r"\b(पेनेट्रेशन\s*टेस्ट|एथिकल\s*हॅकिंग)\b",
        # Transliterated patterns
        r"\b(pentest|penetration\s*test)\b.*\b(karo|karna|chahiye|kay|kara)\b",
    ],
    Intent.CYBERSECURITY: [
        r"\b(cybersecurity|cyber\s*security|defensive\s*security)\b",
        r"\b(threat\s*detection|threat\s*scan|threat\s*analysis)\b",
        r"\b(endpoint\s*security|endpoint\s*check|endpoint\s*scan)\b",
        r"\b(monitor|scan|check)\s*(?:my\s*)?endpoints?\b",
        r"\b(network\s*security|network\s*monitor|network\s*check)\b",
        r"\b(vulnerability\s*scan|vuln\s*scan|patch\s*check)\b",
        r"\b(web\s*security|web\s*app\s*security|web\s*analysis)\b",
        r"\b(code\s*security|code\s*scan|secure\s*code|code\s*analysis)\b",
        r"\b(dependency\s*scan|dependency\s*check|package\s*security)\b",
        r"\b(file\s*integrity|integrity\s*monitor|integrity\s*check|file\s*baseline)\b",
        r"\b(malware\s*analysis|malware\s*scan|suspicious\s*file|file\s*analysis)\b",
        r"\b(log\s*analysis|log\s*scan|event\s*log|security\s*log)\b",
        r"\b(secret\s*scan|credential\s*check|exposed\s*secrets|password\s*scan)\b",
        r"\b(database\s*security|database\s*audit|db\s*security)\b",
        r"\b(security\s*alert|alert\s*manager|active\s*alerts)\b",
        r"\b(incident\s*response|security\s*incident|create\s*incident)\b",
        r"\b(backup\s*security|backup\s*verify|backup\s*integrity)\b",
        r"\b(privacy\s*scan|pii\s*detection|data\s*privacy|redact)\b",
        r"\b(security\s*report|security\s*summary|security\s*status)\b",
        r"\b(security\s*knowledge|owasp|cwe|cve)\b",
        r"\b(full\s*security\s*scan|comprehensive\s*security|run\s*all\s*security)\b",
        r"\b(security\s*dashboard|security\s*overview|security\s*stats)\b",
        r"\b(check|scan|run)\s*(?:for\s*)?(?:threats?|vulnerabilit(?:y|ies))\b",
        r"\b(security|cyber)\b.*\b(status|dashboard|overview|monitor|monitoring)\b",
        r"\b(security|cyber)\b.*\b(scan|check)\b",
        r"\b(threat|malware|ransomware|phishing)\b.*\b(scan|check|detect|monitor)\b",
        r"\b(firewall\s*check|firewall\s*status|firewall\s*monitor)\b",
        r"\b(सुरक्षा\s*स्कॅन|सुरक्षा\s*तपासणी|सायबर\s*सुरक्षा)\b",
    ],
    Intent.INDUSTRIAL: [
        r"\b(plc|hmi|scada)\b",
        r"\b(modbus|opc\s*ua|opcua|mqtt|profinet)\b",
        r"\b(conveyor|actuator|motor\s*control|pid)\b",
        r"\b(machine\s*state|plc\s*tag|industrial)\b.*\b(read|state|status|monitor)\b",
        r"\b(read|show|check)\b.*\b(plc|tag|conveyor|machine)\b",
        r"\b(alarm|interlock|emergency\s*stop)\b.*\b(status|check|state)\b",
    ],
    Intent.PLC: [
        r"\b(ladder\s*logic|structured\s*text|function\s*block)\b",
        r"\b(plc)\b.*\b(analy[sz]e|explain|generate|document|test|code)\b",
        r"\b(analy[sz]e|explain|generate|document)\b.*\b(plc|ladder)\b.*\b(program|code|logic)\b",
        r"\bplc\s*program\b",
    ],
    Intent.MAINTENANCE: [
        r"\b(predictive\s*maintenance|equipment\s*health)\b",
        r"\b(vibration|bearing|wear|failure\s*prediction)\b",
        r"\b(anomaly|trend)\b.*\b(sensor|equipment|machine|motor)\b",
        r"\b(maintenance|health)\b.*\b(check|analy[sz]e|status|report)\b",
    ],
    Intent.CELL_INSPECTION: [
        r"\binspect\b.*\b(robot\s*cell|cell)\b",
        r"\b(robot\s*cell|cell)\b.*\b(inspect|status|report|check)\b",
    ],
    Intent.VISION: [
        r"\b(camera|webcam|yolo|opencv|ocr)\b",
        r"\b(detect|track|recognize|inspect)\b.*\b(object|camera|image|what\s+you\s+see)\b",
        r"\bwhat\s+do\s+you\s+see\b",
        r"\bdefect|barcode|qr\s*code\b",
    ],
}

ENTITY_PATTERNS = {
    "programming_language": r"\b(python|javascript|java|cpp|c\+\+|rust|go|typescript|ruby|php|swift|kotlin)\b",
    "file_type": r"\b(python|javascript|json|yaml|xml|html|css|markdown|txt|csv)\b.*\b(file)\b",
    "action": r"\b(create|read|update|delete|open|close|save|load|export|import)\b",
    "target": r"\b(file|folder|directory|function|class|module|variable|database|api)\b",
}


def classify_intent(text: str) -> IntentResult:
    """Classify the intent of a voice command."""
    text_lower = text.lower().strip()
    scores = {intent: 0.0 for intent in Intent}
    matched_entities = {}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                scores[intent] += len(matches) * 0.3

    for entity_name, pattern in ENTITY_PATTERNS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            matched_entities[entity_name] = list(set(matches))

    total_score = sum(scores.values())
    if total_score == 0:
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            primary_intent=Intent.UNKNOWN,
            secondary_intent=None,
            entities=matched_entities,
            is_multi_intent=False,
        )

    sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_intent, primary_score = sorted_intents[0]

    secondary_intent = None
    is_multi_intent = False
    if len(sorted_intents) > 1:
        sec_intent, sec_score = sorted_intents[1]
        if sec_score > 0 and (sec_score / primary_score) > 0.5:
            secondary_intent = sec_intent
            is_multi_intent = True

    confidence = min(primary_score / max(total_score, 1.0), 1.0)
    confidence = max(confidence, 0.1)

    result = IntentResult(
        intent=primary_intent,
        confidence=confidence,
        primary_intent=primary_intent,
        secondary_intent=secondary_intent,
        entities=matched_entities,
        is_multi_intent=is_multi_intent,
    )

    logger.debug(
        f"Intent classified: {primary_intent.value} (confidence: {confidence:.2f})"
        + (f", secondary: {secondary_intent.value}" if secondary_intent else "")
    )

    return result


def get_intent_description(intent: Intent) -> str:
    """Get a human-readable description of an intent."""
    descriptions = {
        Intent.CODE_GENERATION: "Generate or create code",
        Intent.CODE_EDITING: "Edit or modify existing code",
        Intent.CODE_EXPLANATION: "Explain code functionality",
        Intent.FILE_OPERATION: "Perform file system operations",
        Intent.SYSTEM_CONTROL: "Control system applications and settings",
        Intent.INFORMATION_QUERY: "Search for information",
        Intent.TASK_AUTOMATION: "Automate tasks or workflows",
        Intent.NAVIGATION: "Navigate through UI or content",
        Intent.MEDIA_CONTROL: "Control media playback",
        Intent.CONVERSATION: "General conversation or greetings",
        Intent.VEDIC_KNOWLEDGE: "Query Vedic and Indic knowledge",
        Intent.CAD_MODELING: "Create or modify 3D CAD models",
        Intent.ETHICAL_HACKING: "Run authorized security tests and penetration testing",
        Intent.CYBERSECURITY: "Run defensive security scans, threat detection, and security monitoring",
        Intent.INDUSTRIAL: "Read industrial devices, PLC tags, alarms and machine state",
        Intent.PLC: "Analyze or draft PLC programs",
        Intent.MAINTENANCE: "Analyze equipment health and sensor trends",
        Intent.CELL_INSPECTION: "Inspect the robot cell and correlate all subsystems",
        Intent.VISION: "Process camera input and detect objects",
        Intent.UNKNOWN: "Unclear intent",
    }
    return descriptions.get(intent, "Unknown intent")
