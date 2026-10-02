"""Advanced language detection with confidence scoring and code-switching support.

Provides multilingual language detection for English, Hindi, and Marathi with:
- Confidence scoring (0.0 to 1.0)
- Code-switching detection (mixed language text)
- Language preference learning from user history
- Script detection (Devanagari vs Latin)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Unicode ranges
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[a-zA-Z]")

# Language-specific markers with weights
HINDI_MARKERS = {
    "है": 2.0, "हैं": 2.0, "का": 1.5, "की": 1.5, "के": 1.5, "में": 1.5,
    "को": 1.3, "से": 1.3, "पर": 1.3, "और": 1.8, "या": 1.5, "नहीं": 2.0,
    "क्या": 1.8, "कैसे": 1.8, "कहाँ": 1.8, "कब": 1.5, "मैं": 1.5,
    "तुम": 1.5, "आप": 1.5, "वह": 1.3, "यह": 1.3, "करना": 1.5,
    "जाना": 1.5, "आना": 1.5, "खाना": 1.5, "पीना": 1.5, "सोना": 1.5,
    "the": 0.3, "is": 0.3, "are": 0.3, "in": 0.2, "on": 0.2,  # English loanwords
}

MARATHI_MARKERS = {
    "आहे": 2.5, "आहेत": 2.5, "करा": 2.0, "करो": 2.0, "नाही": 2.5,
    "नको": 2.5, "काय": 2.0, "मी": 1.8, "तुम्ही": 2.0, "आपण": 2.0,
    "झाले": 2.0, "सर": 1.5, "कसा": 2.0, "कशी": 2.0, "ला": 1.5,
    "पाहिजे": 2.0, "साठी": 1.8, "करायचं": 2.5, "धन्यवाद": 2.5,
    "नमस्कार": 2.5, "आणि": 2.0, "पण": 1.8, "किंवा": 2.0,
    "ळ": 2.0, "ഴ": 2.0,  # Unique Marathi letters
}

ENGLISH_MARKERS = {
    "the": 1.5, "is": 1.5, "are": 1.5, "was": 1.5, "were": 1.5,
    "have": 1.5, "has": 1.5, "had": 1.5, "do": 1.3, "does": 1.3,
    "did": 1.3, "will": 1.5, "would": 1.5, "could": 1.5, "should": 1.5,
    "can": 1.3, "may": 1.3, "might": 1.3, "must": 1.3, "shall": 1.3,
    "i": 1.0, "you": 1.0, "he": 1.0, "she": 1.0, "it": 1.0, "we": 1.0,
    "they": 1.0, "me": 1.0, "him": 1.0, "her": 1.0, "us": 1.0, "them": 1.0,
    "my": 1.0, "your": 1.0, "his": 1.0, "its": 1.0, "our": 1.0, "their": 1.0,
    "what": 1.5, "which": 1.5, "who": 1.5, "whom": 1.5, "whose": 1.5,
    "where": 1.5, "when": 1.5, "why": 1.5, "how": 1.5,
    "and": 1.3, "or": 1.3, "but": 1.3, "not": 1.3, "if": 1.3,
    "jarvis": 1.0, "open": 1.0, "create": 1.0, "write": 1.0, "show": 1.0,
}


@dataclass
class LanguageDetection:
    """Result of language detection with confidence scoring."""
    language: str  # 'en', 'hi', 'mr', or 'mixed'
    confidence: float  # 0.0 to 1.0
    primary_language: str  # Dominant language in case of mixing
    secondary_language: Optional[str]  # Secondary language if mixed
    script: str  # 'devanagari', 'latin', or 'mixed'
    code_switching: bool  # True if text contains multiple languages


def detect_script(text: str) -> str:
    """Detect the script used in the text."""
    text = text or ""
    has_devanagari = bool(DEVANAGARI_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))
    
    if has_devanagari and has_latin:
        return "mixed"
    elif has_devanagari:
        return "devanagari"
    else:
        return "latin"


def calculate_language_score(text: str, markers: dict[str, float]) -> float:
    """Calculate language score based on marker matches."""
    text_lower = (text or "").lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    score = 0.0
    for word in words:
        if word in markers:
            score += markers[word]
    
    # Normalize by word count to avoid bias toward longer texts
    if words:
        score = score / len(words)
    
    return score


def detect_code_switching(text: str) -> tuple[bool, str, Optional[str]]:
    """Detect if text contains code-switching between languages."""
    text = text or ""
    
    # Count Devanagari vs Latin words
    devanagari_words = len(DEVANAGARI_RE.findall(text))
    latin_words = len(re.findall(r'[a-zA-Z]+', text))
    
    total = devanagari_words + latin_words
    if total == 0:
        return False, "en", None
    
    devanagari_ratio = devanagari_words / total
    latin_ratio = latin_words / total
    
    # If both scripts present in significant amounts, it's code-switching
    if devanagari_ratio > 0.2 and latin_ratio > 0.2:
        # Determine primary language based on markers
        hindi_score = calculate_language_score(text, HINDI_MARKERS)
        marathi_score = calculate_language_score(text, MARATHI_MARKERS)
        
        if marathi_score > hindi_score:
            return True, "mr", "en"
        elif hindi_score > 0:
            return True, "hi", "en"
        else:
            return True, "en", "hi"
    
    return False, "en", None


def detect_language(text: str) -> LanguageDetection:
    """Detect language with confidence scoring and code-switching support."""
    text = (text or "").strip()
    
    if not text:
        return LanguageDetection(
            language="en",
            confidence=0.0,
            primary_language="en",
            secondary_language=None,
            script="latin",
            code_switching=False,
        )
    
    # Detect script
    script = detect_script(text)
    
    # Check for code-switching
    code_switching, primary, secondary = detect_code_switching(text)
    
    if code_switching:
        # Mixed language text
        confidence = 0.7  # Lower confidence for mixed text
        return LanguageDetection(
            language="mixed",
            confidence=confidence,
            primary_language=primary,
            secondary_language=secondary,
            script=script,
            code_switching=True,
        )
    
    # Calculate scores for each language
    english_score = calculate_language_score(text, ENGLISH_MARKERS)
    hindi_score = calculate_language_score(text, HINDI_MARKERS)
    marathi_score = calculate_language_score(text, MARATHI_MARKERS)
    
    # Script-based boosting
    if script == "devanagari":
        hindi_score *= 1.5
        marathi_score *= 1.5
        english_score *= 0.5
    elif script == "latin":
        english_score *= 1.3
    
    # Determine primary language
    scores = {
        "en": english_score,
        "hi": hindi_score,
        "mr": marathi_score,
    }
    
    max_score = max(scores.values())
    if max_score == 0:
        # No markers found, default to English with low confidence
        return LanguageDetection(
            language="en",
            confidence=0.3,
            primary_language="en",
            secondary_language=None,
            script=script,
            code_switching=False,
        )
    
    # Find language with max score
    detected_lang = max(scores, key=scores.get)
    
    # Calculate confidence based on score magnitude and separation
    sorted_scores = sorted(scores.values(), reverse=True)
    top_score = sorted_scores[0]
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0
    
    # Confidence is higher when top score is much larger than second
    separation = (top_score - second_score) / (top_score + 0.001)
    magnitude = min(top_score / 2.0, 1.0)  # Normalize to 0-1 range
    
    confidence = 0.5 * separation + 0.5 * magnitude
    confidence = max(0.1, min(1.0, confidence))  # Clamp to 0.1-1.0
    
    return LanguageDetection(
        language=detected_lang,
        confidence=confidence,
        primary_language=detected_lang,
        secondary_language=None,
        script=script,
        code_switching=False,
    )


def get_speech_lang_code(detection: LanguageDetection) -> str:
    """Convert language detection to speech recognition lang code."""
    lang_map = {
        "en": "en-IN",
        "hi": "hi-IN",
        "mr": "mr-IN",
    }
    return lang_map.get(detection.primary_language, "en-IN")
