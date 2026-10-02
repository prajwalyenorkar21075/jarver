"""Multilingual understanding for Vedic Knowledge System."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from ..base import Language, VedicDomain

logger = logging.getLogger(__name__)


@dataclass
class TransliterationMap:
    """Mapping for Sanskrit transliteration variants."""
    iast_to_devanagari: dict[str, str]
    common_variants: dict[str, str]


SANSKRIT_TRANSLITERATIONS = TransliterationMap(
    iast_to_devanagari={
        "ā": "आ", "ī": "ई", "ū": "ऊ", "ṛ": "ऋ", "ṝ": "ॠ", "ḷ": "ऌ",
        "ṅ": "ङ", "ñ": "ञ", "ṭ": "ट", "ḍ": "ड", "ṇ": "ण",
        "ś": "श", "ṣ": "ष", "ṃ": "ं", "ḥ": "ः",
        "a": "अ", "i": "इ", "u": "उ", "e": "ए", "o": "ओ",
        "k": "क", "kh": "ख", "g": "ग", "gh": "घ", "ṅ": "ङ",
        "c": "च", "ch": "छ", "j": "ज", "jh": "झ", "ñ": "ञ",
        "t": "त", "th": "थ", "d": "द", "dh": "ध", "n": "न",
        "p": "प", "ph": "फ", "b": "ब", "bh": "भ", "m": "म",
        "y": "य", "r": "र", "l": "ल", "v": "व",
        "h": "ह",
    },
    common_variants={
        "atman": "ātman",
        "atma": "ātman",
        "brahman": "brahman",
        "brahma": "brahman",
        "dharma": "dharma",
        "karma": "karma",
        "moksha": "mokṣa",
        "moksa": "mokṣa",
        "yoga": "yoga",
        "jnana": "jñāna",
        "bhakti": "bhakti",
        "samsara": "saṃsāra",
        "maya": "māyā",
        "avidya": "avidyā",
        "vidya": "vidyā",
        "guru": "guru",
        "shishya": "śiṣya",
        "vedanta": "vedānta",
        "upanishad": "upaniṣad",
        "rishis": "ṛṣi",
        "shruti": "śruti",
        "smriti": "smṛti",
        "prana": "prāṇa",
        "kundalini": "kuṇḍalinī",
        "chakra": "cakra",
        "nadi": "nāḍī",
        "sushumna": "suṣumṇā",
        "ida": "iḍā",
        "pingala": "piṅgalā",
        "om": "oṃ",
        "aum": "oṃ",
        "pranava": "praṇava",
        "gayatri": "gāyatrī",
        "savitr": "sāvitṛ",
        "surya": "sūrya",
        "agni": "agni",
        "vayu": "vāyu",
        "varuna": "varuṇa",
        "indra": "indra",
        "soma": "soma",
        "rudra": "rudra",
        "vishnu": "viṣṇu",
        "shiva": "śiva",
        "devi": "devī",
        "durga": "durgā",
        "lakshmi": "lakṣmī",
        "saraswati": "sarasvatī",
        "ganesha": "gaṇeśa",
        "hanuman": "hanumān",
        "rama": "rāma",
        "krishna": "kṛṣṇa",
        "arjuna": "arjuna",
        "bhishma": "bhīṣma",
        "drona": "droṇa",
        "karna": "karṇa",
        "yudhishthira": "yudhiṣṭhira",
        "bhima": "bhīma",
        "nakula": "nakula",
        "sahadeva": "sahadeva",
        "draupadi": "draupadī",
        "kunti": "kuntī",
        "gandhari": "gāndhārī",
        "dhritarashtra": "dhṛtarāṣṭra",
        "vidura": "vidura",
        "sanjaya": "sañjaya",
        "valmiki": "vālmīki",
        "vyasa": "vyāsa",
        "vashishtha": "vasiṣṭha",
        "vishwamitra": "viśvāmitra",
        "parashara": "parāśara",
        "kapila": "kapila",
        "patanjali": "patañjali",
        "yajnavalkya": "yājñavalkya",
        "shankara": "śaṅkara",
        "ramanuja": "rāmānuja",
        "madhva": "madhva",
    }
)


HINDI_TERMS = {
    "atman": ["आत्मा", "आत्मन्", "आत्म"],
    "brahman": ["ब्रह्म", "ब्रह्मन्"],
    "dharma": ["धर्म"],
    "karma": ["कर्म"],
    "moksha": ["मोक्ष"],
    "yoga": ["योग"],
    "jnana": ["ज्ञान"],
    "bhakti": ["भक्ति"],
    "guru": ["गुरु"],
    "shishya": ["शिष्य"],
    "vedanta": ["वेदांत"],
    "upanishad": ["उपनिषद्"],
    "rishi": ["ऋषि"],
    "shruti": ["श्रुति"],
    "smriti": ["स्मृति"],
    "prana": ["प्राण"],
    "kundalini": ["कुण्डलिनी"],
    "chakra": ["चक्र"],
    "nadi": ["नाड़ी"],
    "om": ["ॐ"],
    "gayatri": ["गायत्री"],
    "surya": ["सूर्य"],
    "agni": ["अग्नि"],
    "vayu": ["वायु"],
    "varuna": ["वरुण"],
    "indra": ["इन्द्र"],
    "soma": ["सोम"],
    "rudra": ["रुद्र"],
    "vishnu": ["विष्णु"],
    "shiva": ["शिव"],
    "devi": ["देवी"],
    "durga": ["दुर्गा"],
    "lakshmi": ["लक्ष्मी"],
    "saraswati": ["सरस्वती"],
    "ganesha": ["गणेश"],
    "hanuman": ["हनुमान"],
    "rama": ["राम"],
    "krishna": ["कृष्ण"],
    "arjuna": ["अर्जुन"],
    "bhishma": ["भीष्म"],
    "drona": ["द्रोण"],
    "karna": ["कर्ण"],
    "yudhishthira": ["युधिष्ठिर"],
    "bhima": ["भीम"],
    "nakula": ["नकुल"],
    "sahadeva": ["सहदेव"],
    "draupadi": ["द्रौपदी"],
    "kunti": ["कुंती"],
    "gandhari": ["गांधारी"],
    "dhritarashtra": ["धृतराष्ट्र"],
    "vidura": ["विदुर"],
    "sanjaya": ["संजय"],
    "valmiki": ["वाल्मीकि"],
    "vyasa": ["व्यास"],
    "vashishtha": ["वशिष्ठ"],
    "vishwamitra": ["विश्वामित्र"],
    "parashara": ["पराशर"],
    "kapila": ["कपिल"],
    "patanjali": ["पतञ्जलि"],
    "yajnavalkya": ["याज्ञवल्क्य"],
    "shankara": ["शङ्कर"],
    "ramanuja": ["रामानुज"],
    "madhva": ["मध्व"],
}


MARATHI_TERMS = {
    "atman": ["आत्मा", "आत्मन्"],
    "brahman": ["ब्रह्म", "ब्रह्मन्"],
    "dharma": ["धर्म"],
    "karma": ["कर्म"],
    "moksha": ["मोक्ष"],
    "yoga": ["योग"],
    "jnana": ["ज्ञान"],
    "bhakti": ["भक्ती"],
    "guru": ["गुरू"],
    "shishya": ["शिष्य"],
    "vedanta": ["वेदांत"],
    "upanishad": ["उपनिषद्"],
    "rishi": ["ऋषी"],
    "shruti": ["श्रुती"],
    "smriti": ["स्मृती"],
    "prana": ["प्राण"],
    "kundalini": ["कुण्डलिनी"],
    "chakra": ["चक्र"],
    "nadi": ["नाडी"],
    "om": ["ॐ"],
    "gayatri": ["गायत्री"],
    "surya": ["सूर्य"],
    "agni": ["अग्नि"],
    "vayu": ["वायू"],
    "varuna": ["वरुण"],
    "indra": ["इन्द्र"],
    "soma": ["सोम"],
    "rudra": ["रुद्र"],
    "vishnu": ["विष्णू"],
    "shiva": ["शिव"],
    "devi": ["देवी"],
    "durga": ["दुर्गा"],
    "lakshmi": ["लक्ष्मी"],
    "saraswati": ["सरस्वती"],
    "ganesha": ["गणेश"],
    "hanuman": ["हनुमान"],
    "rama": ["राम"],
    "krishna": ["कृष्ण"],
    "arjuna": ["अर्जुन"],
    "bhishma": ["भीष्म"],
    "drona": ["द्रोण"],
    "karna": ["कर्ण"],
    "yudhishthira": ["युधिष्ठीर"],
    "bhima": ["भीम"],
    "nakula": ["नकुल"],
    "sahadeva": ["सहदेव"],
    "draupadi": ["द्रौपदी"],
    "kunti": ["कुंती"],
    "gandhari": ["गांधारी"],
    "dhritarashtra": ["धृतराष्ट्र"],
    "vidura": ["विदुर"],
    "sanjaya": ["संजय"],
    "valmiki": ["वाल्मिकी"],
    "vyasa": ["व्यास"],
    "vashishtha": ["वशिष्ठ"],
    "vishwamitra": ["विश्वामित्र"],
    "parashara": ["पराशर"],
    "kapila": ["कपील"],
    "patanjali": ["पतंजली"],
    "yajnavalkya": ["याज्ञवल्क्य"],
    "shankara": ["शंकर"],
    "ramanuja": ["रामानुज"],
    "madhva": ["मध्व"],
}


HINGLISH_PATTERNS = [
    (r"atman\s+mhanje\s+kay", "atman meaning"),
    (r"brahman\s+kya\s+hai", "brahman meaning"),
    (r"gita\s+madhla\s+karma\s+yoga", "gita karma yoga"),
    (r"gita\s+madhla\s+jnana\s+yoga", "gita jnana yoga"),
    (r"gita\s+madhla\s+bhakti\s+yoga", "gita bhakti yoga"),
    (r"upanishads?\s+ani\s+gita", "upanishads and gita"),
    (r"mahabharat\s+madhla\s+gita", "mahabharata gita"),
    (r"vedanga\s+ka\s+important", "vedangas importance"),
    (r"(\w+)\s+mhanje\s+kay", r"\1 meaning"),
    (r"(\w+)\s+ka\s+matlab", r"\1 meaning"),
    (r"(\w+)\s+explain\s+kar", r"explain \1"),
    (r"(\w+)\s+compare\s+kar", r"compare \1"),
]


def detect_language(text: str) -> Language:
    """Detect the language of the input text."""
    text_lower = text.lower().strip()

    # Check for Devanagari script (Hindi/Marathi/Sanskrit)
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
    if devanagari_chars > len(text) * 0.3:
        # Could be Hindi, Marathi, or Sanskrit - check specific terms
        for term, variants in HINDI_TERMS.items():
            if any(v in text for v in variants):
                return Language.HINDI
        for term, variants in MARATHI_TERMS.items():
            if any(v in text for v in variants):
                return Language.MARATHI
        return Language.HINDI  # Default to Hindi for Devanagari

    # Check for Hinglish patterns
    for pattern, _ in HINGLISH_PATTERNS:
        if re.search(pattern, text_lower):
            return Language.HINGLISH

    # Check for Marathi-English mix
    if re.search(r"\b(madhla|madhye|kasa|kay|ahe|nahi|ho)\b", text_lower):
        return Language.MARATHI_ENGLISH

    # Check for Hindi-English mix
    if re.search(r"\b(kya|hai|koi|kuch|bhi|nahin|hai)\b", text_lower):
        return Language.HINDI_ENGLISH

    return Language.ENGLISH


def normalize_sanskrit_term(term: str) -> str:
    """Normalize Sanskrit term to IAST standard."""
    term_lower = term.lower().strip()
    return SANSKRIT_TRANSLITERATIONS.common_variants.get(term_lower, term_lower)


def extract_sanskrit_terms(text: str) -> list[str]:
    """Extract and normalize Sanskrit terms from text."""
    terms = set()
    text_lower = text.lower()

    # Direct matches from common variants
    for variant, standard in SANSKRIT_TRANSLITERATIONS.common_variants.items():
        if variant in text_lower:
            terms.add(standard)

    # Devanagari matches
    for term, variants in HINDI_TERMS.items():
        if any(v in text for v in variants):
            terms.add(normalize_sanskrit_term(term))

    for term, variants in MARATHI_TERMS.items():
        if any(v in text for v in variants):
            terms.add(normalize_sanskrit_term(term))

    return list(terms)


def translate_query_to_english(query: str) -> str:
    """Translate multilingual query to English for processing."""
    lang = detect_language(query)

    if lang == Language.ENGLISH:
        return query

    translated = query

    # Handle Hinglish patterns
    for pattern, replacement in HINGLISH_PATTERNS:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

    # Replace Devanagari terms with English equivalents
    for term, variants in HINDI_TERMS.items():
        for variant in variants:
            if variant in translated:
                translated = translated.replace(variant, term)

    for term, variants in MARATHI_TERMS.items():
        for variant in variants:
            if variant in translated:
                translated = translated.replace(variant, term)

    return translated


def get_multilingual_keywords(concept: str) -> dict[Language, list[str]]:
    """Get keywords for a concept in all supported languages."""
    normalized = normalize_sanskrit_term(concept)

    result = {
        Language.ENGLISH: [normalized],
        Language.HINDI: [],
        Language.MARATHI: [],
        Language.SANSKRIT: [],
        Language.HINGLISH: [],
        Language.HINDI_ENGLISH: [],
        Language.MARATHI_ENGLISH: [],
    }

    # Add Devanagari variants
    if normalized in HINDI_TERMS:
        result[Language.HINDI] = HINDI_TERMS[normalized]
        result[Language.SANSKRIT] = HINDI_TERMS[normalized]

    if normalized in MARATHI_TERMS:
        result[Language.MARATHI] = MARATHI_TERMS[normalized]

    # Add Hinglish variants
    hinglish_forms = [
        f"{normalized} mhanje kay",
        f"{normalized} kya hai",
        f"{normalized} ka matlab",
        f"explain {normalized}",
    ]
    result[Language.HINGLISH] = hinglish_forms

    return result


class MultilingualQueryProcessor:
    """Process queries in multiple languages."""

    def __init__(self):
        self._cache: dict[str, tuple[Language, str, list[str]]] = {}

    def process(self, query: str) -> tuple[Language, str, list[str]]:
        """Process a query and return (detected_language, english_query, sanskrit_terms)."""
        cache_key = query.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]

        language = detect_language(query)
        english_query = translate_query_to_english(query)
        sanskrit_terms = extract_sanskrit_terms(query)

        result = (language, english_query, sanskrit_terms)
        self._cache[cache_key] = result
        return result


# Singleton instance
_processor: MultilingualQueryProcessor | None = None


def get_multilingual_processor() -> MultilingualQueryProcessor:
    global _processor
    if _processor is None:
        _processor = MultilingualQueryProcessor()
    return _processor