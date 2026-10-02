"""Indian Knowledge Base — structured knowledge for Vedic literature, philosophy, and spiritual traditions."""

from .base import KnowledgeEntry, KnowledgeDomain, KnowledgeBase
from .engine import KnowledgeEngine, QueryResult
from .embeddings import EmbeddingEngine, ChunkMetadata, get_embedding_engine, build_embeddings_from_kb
from .concept_graph import ConceptGraph, get_concept_graph
from .multilingual import MultilingualProcessor, get_multilingual_processor, SupportedLanguage, detect_language
from .web_fallback import WebIngestionPipeline, search_web, fetch_and_validate, WebSource, SourceType, ValidationStatus
from .corpus_manager import CorpusManager, get_corpus_manager, CorpusValidationReport

__all__ = [
    "KnowledgeEntry",
    "KnowledgeDomain",
    "KnowledgeBase",
    "KnowledgeEngine",
    "QueryResult",
    "EmbeddingEngine",
    "ChunkMetadata",
    "get_embedding_engine",
    "build_embeddings_from_kb",
    "ConceptGraph",
    "get_concept_graph",
    "MultilingualProcessor",
    "get_multilingual_processor",
    "SupportedLanguage",
    "detect_language",
    "WebIngestionPipeline",
    "search_web",
    "fetch_and_validate",
    "WebSource",
    "SourceType",
    "ValidationStatus",
    "CorpusManager",
    "get_corpus_manager",
    "CorpusValidationReport",
]
