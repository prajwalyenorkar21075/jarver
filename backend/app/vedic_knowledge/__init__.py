"""Vedic Knowledge System — source-aware, multilingual, provenance-tracked."""

from .base import (
    KnowledgeChunk,
    VedicKnowledgeEntry,
    VedicKnowledgeDomain,
    VedicKnowledgeBase,
    SourceMetadata,
    QueryResult,
    WebSearchResult,
    DifficultyLevel,
    SourceType,
    Language,
    VedicDomain,
)
from .engine import VedicKnowledgeEngine, ExplainResult
from .agent import VedicKnowledgeAgent, AgentResponse, create_vedic_knowledge_agent
from .multilingual.processor import (
    detect_language,
    normalize_sanskrit_term,
    extract_sanskrit_terms,
    translate_query_to_english,
    get_multilingual_keywords,
    MultilingualQueryProcessor,
    get_multilingual_processor,
)
from .rag.retriever import SemanticRetriever, HybridRetriever, RetrievalConfig, RetrievalResult
from .web.search import get_web_search_client, WebSearchClient, WebSearchConfig, SourceInspector, WebKnowledgeExtractor
from .ingestion.ingester import DocumentIngester, CorpusManager, IngestionConfig, IngestionResult
from .validation.validator import SourceValidator, CorpusValidator, ValidationResult, get_source_validator
from .domains.loader import load_all_domains

__all__ = [
    # Base
    "KnowledgeChunk",
    "VedicKnowledgeEntry",
    "VedicKnowledgeDomain",
    "VedicKnowledgeBase",
    "SourceMetadata",
    "QueryResult",
    "WebSearchResult",
    "DifficultyLevel",
    "SourceType",
    "Language",
    "VedicDomain",
    # Engine
    "VedicKnowledgeEngine",
    "ExplainResult",
    # Agent
    "VedicKnowledgeAgent",
    "AgentResponse",
    "create_vedic_knowledge_agent",
    # Domains
    "load_all_domains",
    # Multilingual
    "detect_language",
    "normalize_sanskrit_term",
    "extract_sanskrit_terms",
    "translate_query_to_english",
    "get_multilingual_keywords",
    "MultilingualQueryProcessor",
    "get_multilingual_processor",
    # RAG
    "SemanticRetriever",
    "HybridRetriever",
    "RetrievalConfig",
    "RetrievalResult",
    # Web
    "get_web_search_client",
    "WebSearchClient",
    "WebSearchConfig",
    "SourceInspector",
    "WebKnowledgeExtractor",
    # Ingestion
    "DocumentIngester",
    "CorpusManager",
    "IngestionConfig",
    "IngestionResult",
    # Validation
    "SourceValidator",
    "CorpusValidator",
    "ValidationResult",
    "get_source_validator",
]