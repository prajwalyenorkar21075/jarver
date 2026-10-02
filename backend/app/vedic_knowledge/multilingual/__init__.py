"""Multilingual Understanding."""

from .processor import (
    detect_language,
    normalize_sanskrit_term,
    extract_sanskrit_terms,
    translate_query_to_english,
    get_multilingual_keywords,
    MultilingualQueryProcessor,
    get_multilingual_processor,
)

__all__ = [
    "detect_language",
    "normalize_sanskrit_term",
    "extract_sanskrit_terms",
    "translate_query_to_english",
    "get_multilingual_keywords",
    "MultilingualQueryProcessor",
    "get_multilingual_processor",
]