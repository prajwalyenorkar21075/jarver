"""Multilingual support for Vedic knowledge queries."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    SANSKRIT = "sa"
    HINGLISH = "hi-en"
    MARATHLISH = "mr-en"


@dataclass
class LanguageDetectionResult:
    language: SupportedLanguage
    confidence: float
    detected_script: str
    is_code_mixed: bool


TRANSLITERATION_MAP = {
    "a": "अ", "aa": "आ", "A": "आ", "i": "इ", "ii": "ई", "I": "ई",
    "u": "उ", "uu": "ऊ", "U": "ऊ", "ri": "ऋ", "R": "ऋ",
    "e": "ए", "ai": "ऐ", "o": "ओ", "au": "औ",
    "ka": "क", "kha": "ख", "ga": "ग", "gha": "घ", "na": "ङ",
    "ca": "च", "cha": "छ", "ja": "ज", "jha": "झ", "nya": "ञ",
    "ta": "ट", "tha": "ठ", "da": "ड", "dha": "ढ", "Na": "ण",
    "ta": "त", "tha": "थ", "da": "द", "dha": "ध", "na": "न",
    "pa": "प", "pha": "फ", "ba": "ब", "bha": "भ", "ma": "म",
    "ya": "य", "ra": "र", "la": "ल", "va": "व",
    "sha": "श", "Sha": "ष", "sa": "स", "ha": "ह",
    "ksha": "क्ष", "tra": "त्र", "jna": "ज्ञ",
    "M": "ं", "H": "ः", "m": "म्", "n": "न्",
}


CONCEPT_TRANSLITERATIONS = {
    "atman": ["atman", "ātman", "aatman", "आत्मन्", "आत्मा", "atma"],
    "brahman": ["brahman", "brahman", "ब्रह्मन्", "ब्रह्मा", "brahma"],
    "dharma": ["dharma", "धर्म", "dharm"],
    "karma": ["karma", "कर्म", "karm"],
    "moksha": ["moksha", "mokṣa", "मोक्ष", "moksa"],
    "yoga": ["yoga", "योग", "yog"],
    "jnana": ["jnana", "jñāna", "ज्ञान", "gyan", "jnan"],
    "bhakti": ["bhakti", "भक्ति", "bhakt"],
    "karma_yoga": ["karma yoga", "कर्म योग", "karm yog"],
    "jnana_yoga": ["jnana yoga", "ज्ञान योग", "gyan yog"],
    "bhakti_yoga": ["bhakti yoga", "भक्ति योग", "bhakt yog"],
    "dhyana": ["dhyana", "ध्यान", "dhyan"],
    "prakriti": ["prakriti", "प्रकृति", "prakruti"],
    "purusha": ["purusha", "पुरुष", "purush"],
    "upanishad": ["upanishad", "उपनिषद्", "upanisad"],
    "brahmana": ["brahmana", "ब्राह्मण", "brahman"],
    "aranyaka": ["aranyaka", "आरण्यक"],
    "vedanga": ["vedanga", "वेदाङ्ग", "vedang"],
    "shiksha": ["shiksha", "शिक्षा", "siksha"],
    "kalpa": ["kalpa", "कल्प"],
    "vyakarana": ["vyakarana", "व्याकरण", "vyakaran"],
    "nirukta": ["nirukta", "निरुक्त"],
    "chandas": ["chandas", "छन्दस्", "chhandas"],
    "jyotisha": ["jyotisha", "ज्योतिष", "jyotish"],
    "ramayana": ["ramayana", "रामायण", "ramayan"],
    "mahabharata": ["mahabharata", "महाभारत", "mahabharat"],
    "purana": ["purana", "पुराण", "puran"],
    "bhagavad_gita": ["bhagavad gita", "भगवद्गीता", "gita", "गीता"],
    "krishna": ["krishna", "कृष्ण", "krsna"],
    "arjuna": ["arjuna", "अर्जुन"],
    "vedas": ["vedas", "वेद", "ved"],
    "rig_veda": ["rig veda", "ऋग्वेद", "rigveda"],
    "sama_veda": ["sama veda", "सामवेद", "samaveda"],
    "yajur_veda": ["yajur veda", "यजुर्वेद", "yajurveda"],
    "atharva_veda": ["atharva veda", "अथर्ववेद", "atharvaveda"],
}


DEVANAGARI_TO_ROMAN = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "क": "ka", "ख": "kha", "ग": "ga", "घ": "gha", "ङ": "na",
    "च": "ca", "छ": "cha", "ज": "ja", "झ": "jha", "ञ": "nya",
    "ट": "ta", "ठ": "tha", "ड": "da", "ढ": "dha", "ण": "Na",
    "त": "ta", "थ": "tha", "द": "da", "ध": "dha", "न": "na",
    "प": "pa", "फ": "pha", "ब": "ba", "भ": "bha", "म": "ma",
    "य": "ya", "र": "ra", "ल": "la", "व": "va",
    "श": "sha", "ष": "Sha", "स": "sa", "ह": "ha",
    "क्ष": "ksha", "त्र": "tra", "ज्ञ": "jna",
    "ं": "M", "ः": "H", "्": "",
    "ा": "a", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
}


MARATHI_TERMS = {
    "काय": "what", "कसे": "how", "कुठे": "where", "कोण": "who", "केव्हा": "when", "का": "why",
    "म्हणजे": "means", "समजाव": "explain", "सांगा": "tell", "दाखवा": "show",
    "आणि": "and", "किंवा": "or", "पण": "but", "कारण": "because",
    "आहे": "is", "होते": "was", "असेल": "will be",
    "मी": "I", "आम्ही": "we", "तो": "he", "ती": "she", "ते": "it",
}

HINDI_TERMS = {
    "क्या": "what", "कैसे": "how", "कहाँ": "where", "कौन": "who", "कब": "when", "क्यों": "why",
    "मतलब": "means", "समझाओ": "explain", "बताओ": "tell", "दिखाओ": "show",
    "और": "and", "या": "or", "लेकिन": "but", "क्योंकि": "because",
    "है": "is", "था": "was", "होगा": "will be",
    "मैं": "I", "हम": "we", "वह": "he/she", "यह": "this",
}


def detect_language(text: str) -> LanguageDetectionResult:
    text_lower = text.lower().strip()

    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = devanagari_chars + latin_chars

    if total_chars == 0:
        return LanguageDetectionResult(SupportedLanguage.ENGLISH, 0.5, "unknown", False)

    devanagari_ratio = devanagari_chars / total_chars

    marathi_words = sum(1 for w in MARATHI_TERMS if w in text)
    hindi_words = sum(1 for w in HINDI_TERMS if w in text)

    is_code_mixed = (devanagari_chars > 0 and latin_chars > 0) or (marathi_words > 0 and latin_chars > 0) or (hindi_words > 0 and latin_chars > 0)

    if devanagari_ratio > 0.7:
        if marathi_words > hindi_words:
            return LanguageDetectionResult(SupportedLanguage.MARATHI, 0.9, "devanagari", is_code_mixed)
        return LanguageDetectionResult(SupportedLanguage.HINDI, 0.9, "devanagari", is_code_mixed)

    if marathi_words > 0 and latin_chars > 0:
        return LanguageDetectionResult(SupportedLanguage.MARATHLISH, 0.85, "mixed", True)
    if hindi_words > 0 and latin_chars > 0:
        return LanguageDetectionResult(SupportedLanguage.HINGLISH, 0.85, "mixed", True)
    if marathi_words > 0:
        return LanguageDetectionResult(SupportedLanguage.MARATHI, 0.8, "romanized", False)
    if hindi_words > 0:
        return LanguageDetectionResult(SupportedLanguage.HINDI, 0.8, "romanized", False)

    return LanguageDetectionResult(SupportedLanguage.ENGLISH, 0.7, "latin", is_code_mixed)


def normalize_concept_term(term: str) -> list[str]:
    term_lower = term.lower().strip()
    normalized = []

    for canonical, variants in CONCEPT_TRANSLITERATIONS.items():
        if term_lower in [v.lower() for v in variants]:
            normalized.append(canonical)
            normalized.extend(variants)

    if not normalized:
        normalized.append(term_lower)

    return list(set(normalized))


def expand_query_with_transliterations(query: str) -> list[str]:
    expanded = [query]
    words = query.lower().split()

    for i, word in enumerate(words):
        normalized = normalize_concept_term(word)
        if len(normalized) > 1:
            for variant in normalized[1:]:
                new_words = words.copy()
                new_words[i] = variant
                expanded.append(" ".join(new_words))

    return list(set(expanded))


def translate_to_english(text: str, source_lang: SupportedLanguage) -> str:
    if source_lang == SupportedLanguage.ENGLISH:
        return text

    result = text
    term_map = {}

    if source_lang in (SupportedLanguage.MARATHI, SupportedLanguage.MARATHLISH):
        term_map.update(MARATHI_TERMS)
    if source_lang in (SupportedLanguage.HINDI, SupportedLanguage.HINGLISH):
        term_map.update(HINDI_TERMS)

    for devanagari, english in term_map.items():
        result = result.replace(devanagari, english)

    return result


def romanize_devanagari(text: str) -> str:
    result = ""
    i = 0
    while i < len(text):
        char = text[i]
        if char in DEVANAGARI_TO_ROMAN:
            result += DEVANAGARI_TO_ROMAN[char]
        else:
            result += char
        i += 1
    return result


def get_concept_in_language(concept: str, target_lang: SupportedLanguage) -> str:
    canonical = concept.lower().strip()

    for c, variants in CONCEPT_TRANSLITERATIONS.items():
        if canonical == c or canonical in [v.lower() for v in variants]:
            if target_lang == SupportedLanguage.HINDI or target_lang == SupportedLanguage.MARATHI:
                for v in variants:
                    if any('\u0900' <= ch <= '\u097F' for ch in v):
                        return v
            elif target_lang in (SupportedLanguage.HINGLISH, SupportedLanguage.MARATHLISH):
                return c.replace("_", " ")
            return c.replace("_", " ")

    return concept


_multilingual_processor = None


def get_multilingual_processor():
    global _multilingual_processor
    if _multilingual_processor is None:
        _multilingual_processor = MultilingualProcessor()
    return _multilingual_processor


class MultilingualProcessor:
    """High-level multilingual query processor."""

    def __init__(self):
        self.detection_cache: dict[str, LanguageDetectionResult] = {}

    def process_query(self, query: str) -> dict:
        detection = detect_language(query)
        self.detection_cache[query] = detection

        expanded_queries = expand_query_with_transliterations(query)
        english_query = translate_to_english(query, detection.language)

        return {
            "original_query": query,
            "detected_language": detection.language.value,
            "confidence": detection.confidence,
            "is_code_mixed": detection.is_code_mixed,
            "expanded_queries": expanded_queries,
            "english_query": english_query,
            "normalized_terms": {w: normalize_concept_term(w) for w in query.split()},
        }

    def format_response(self, content: str, target_lang: SupportedLanguage, depth: str = "normal") -> str:
        if target_lang == SupportedLanguage.ENGLISH:
            return content

        if target_lang in (SupportedLanguage.HINDI, SupportedLanguage.MARATHI):
            return self._translate_response(content, target_lang)

        return content

    def _translate_response(self, content: str, target_lang: SupportedLanguage) -> str:
        term_map = {}
        if target_lang == SupportedLanguage.HINDI:
            term_map = {v: k for k, v in HINDI_TERMS.items()}
        elif target_lang == SupportedLanguage.MARATHI:
            term_map = {v: k for k, v in MARATHI_TERMS.items()}

        result = content
        for english, local in term_map.items():
            result = result.replace(english, local)

        return result