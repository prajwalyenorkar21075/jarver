"""Unified knowledge / RAG layer for JARVIS.

One retrieval interface over the knowledge corpora that already exist in the
project, with real ingestion for operator documents:

    * robotics_knowledge   (ROS2, PLC, HMI/SCADA, CV, AI/ML, automation, ...)
    * indian_knowledge     (Vedic / Indic corpus)
    * cybersecurity        (OWASP/CWE knowledge base)
    * ingested documents   (operator-added text/markdown, chunked + indexed)

Retrieval is lexical (BM25-style scoring) with an optional vector pass when
``sentence-transformers`` is installed. **No answer is invented**: if nothing is
retrieved, the caller is told retrieval failed and given the reason.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.knowledge")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jarvis_persistent.db"

DOMAIN_ALIASES = {
    "cybersecurity": ["cybersecurity", "security", "owasp", "cwe", "cve", "threat"],
    "robotics": ["robotics", "robot", "ros2", "ros", "kinematics", "slam", "navigation"],
    "plc": ["plc", "ladder", "structured text", "iec 61131", "tag"],
    "automation": ["automation", "conveyor", "cell", "industrial"],
    "scada": ["scada", "hmi", "alarm", "trend"],
    "industrial_protocols": ["modbus", "opc ua", "opcua", "mqtt", "profinet", "ethernet/ip"],
    "computer_vision": ["vision", "opencv", "yolo", "detection", "ocr", "segmentation"],
    "ai_ml": ["ai", "ml", "machine learning", "deep learning", "neural"],
    "cad": ["cad", "geometry", "parametric", "extrude", "revolve", "step", "stl"],
    "engineering": ["engineering", "tolerance", "material", "drawing"],
    "documents": ["document", "manual", "procedure", "sop", "datasheet"],
}


@dataclass
class KnowledgeChunk:
    id: str
    text: str
    source: str
    domain: str
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text[:2000],
            "source": self.source,
            "domain": self.domain,
            "title": self.title,
            "metadata": self.metadata,
            "score": round(self.score, 4),
        }


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1]


class UnifiedKnowledgeBase:
    """Retrieval across every knowledge source in the project."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._robotics_kb = None
        self._indian_engine = None
        self._security_kb = None
        self._chunk_cache: list[KnowledgeChunk] = []
        self._cache_built = False
        self._idf: dict[str, float] = {}
        self._ensure_schema()

    # ------------------------------------------------------------------ #
    # Storage for ingested documents
    # ------------------------------------------------------------------ #
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_documents (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        source TEXT,
                        domain TEXT,
                        content TEXT,
                        chunk_count INTEGER,
                        ingested_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT,
                        chunk_index INTEGER,
                        text TEXT,
                        domain TEXT,
                        metadata TEXT,
                        ingested_at REAL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kchunk_doc ON knowledge_chunks(document_id)")
                conn.commit()
            logger.info("[KNOWLEDGE] knowledge documents/chunks tables ready")
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] schema setup failed: {e}")

    # ------------------------------------------------------------------ #
    # Existing corpora
    # ------------------------------------------------------------------ #
    def _load_robotics(self):
        if self._robotics_kb is not None:
            return self._robotics_kb
        try:
            from .robotics_knowledge import KnowledgeBase
            from .robotics_knowledge.domains import load_all_domains
            self._robotics_kb = load_all_domains()
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] robotics corpus unavailable: {e}")
            self._robotics_kb = False
        return self._robotics_kb

    def _load_indian(self):
        if self._indian_engine is not None:
            return self._indian_engine
        try:
            from .indian_knowledge.domains import load_all_domains as load_indian_domains
            from .indian_knowledge.engine import KnowledgeEngine
            base = load_indian_domains()  # returns a populated KnowledgeBase
            self._indian_engine = KnowledgeEngine(base)
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] indian corpus unavailable: {e}")
            self._indian_engine = False
        return self._indian_engine

    def _load_security(self):
        if self._security_kb is not None:
            return self._security_kb
        try:
            from .cybersecurity import get_security_knowledge_base
            self._security_kb = get_security_knowledge_base()
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] security knowledge base unavailable: {e}")
            self._security_kb = False
        return self._security_kb

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    def ingest_text(self, title: str, content: str, domain: str = "documents",
                    source: str = "", chunk_size: int = 900, overlap: int = 120) -> dict[str, Any]:
        if not content or not content.strip():
            return {"success": False, "error": "content is required"}

        chunks = _chunk_text(content, chunk_size, overlap)
        document_id = str(uuid.uuid4())[:12]
        now = time.time()

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO knowledge_documents (id, title, source, domain, content, chunk_count, ingested_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (document_id, title, source, domain, content[:20000], len(chunks), now),
            )
            for index, chunk in enumerate(chunks):
                conn.execute(
                    "INSERT INTO knowledge_chunks (id, document_id, chunk_index, text, domain, metadata, ingested_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (f"{document_id}-{index}", document_id, index, chunk, domain,
                     json.dumps({"title": title, "source": source}), now),
                )
            conn.commit()

        self._cache_built = False
        logger.info(f"[KNOWLEDGE] Ingested '{title}' -> {len(chunks)} chunks (domain={domain})")
        return {"success": True, "document_id": document_id, "title": title,
                "chunks": len(chunks), "domain": domain}

    def ingest_file(self, path: str, domain: str = "documents") -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {path}"}
        suffix = p.suffix.lower()
        try:
            if suffix == ".pdf":
                try:
                    import PyPDF2  # type: ignore
                except ImportError:
                    return {"success": False,
                            "error": "PDF ingestion requires PyPDF2 (pip install PyPDF2)"}
                with open(p, "rb") as handle:
                    reader = PyPDF2.PdfReader(handle)
                    content = "\n".join((page.extract_text() or "") for page in reader.pages)
            elif suffix == ".docx":
                try:
                    import docx  # type: ignore
                except ImportError:
                    return {"success": False,
                            "error": "DOCX ingestion requires python-docx (pip install python-docx)"}
                doc = docx.Document(str(p))
                content = "\n".join(para.text for para in doc.paragraphs)
            else:
                content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"success": False, "error": f"Could not read {path}: {e}"}

        if not content.strip():
            return {"success": False, "error": f"No extractable text in {path}"}
        return self.ingest_text(title=p.name, content=content, domain=domain, source=str(p))

    def list_documents(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, source, domain, chunk_count, ingested_at "
                "FROM knowledge_documents ORDER BY ingested_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, document_id: str) -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT id FROM knowledge_documents WHERE id=?", (document_id,)).fetchone()
            if not row:
                return {"success": False, "error": f"Document '{document_id}' not found"}
            conn.execute("DELETE FROM knowledge_chunks WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM knowledge_documents WHERE id=?", (document_id,))
            conn.commit()
        self._cache_built = False
        return {"success": True, "deleted": document_id}

    # ------------------------------------------------------------------ #
    # Corpus assembly
    # ------------------------------------------------------------------ #
    def _build_cache(self):
        if self._cache_built:
            return
        chunks: list[KnowledgeChunk] = []

        robotics = self._load_robotics()
        if robotics:
            for domain_name in robotics.list_domains():
                domain = robotics.get_domain(domain_name)
                if not domain:
                    continue
                for entry in domain.entries.values():
                    chunks.append(KnowledgeChunk(
                        id=f"rb:{entry.id}",
                        text=f"{entry.title}\n{entry.content}",
                        source="robotics_knowledge",
                        domain=_normalize_domain(domain_name, entry.tags),
                        title=entry.title,
                        metadata={"tags": entry.tags, "difficulty": entry.difficulty.value,
                                  "category": entry.category},
                    ))

        indian = self._load_indian()
        if indian:
            try:
                for domain_name in indian.kb.list_domains():
                    domain = indian.kb.get_domain(domain_name)
                    if not domain:
                        continue
                    for entry in domain.entries.values():
                        chunks.append(KnowledgeChunk(
                            id=f"ik:{entry.id}",
                            text=f"{entry.title}\n{entry.content}",
                            source="indian_knowledge",
                            domain="indic_knowledge",
                            title=entry.title,
                            metadata={"tags": entry.tags, "category": entry.category},
                        ))
            except Exception as e:
                logger.debug(f"[KNOWLEDGE] indian cache skipped: {e}")

        security = self._load_security()
        if security:
            try:
                for item in security.get_owasp_top_10():
                    chunks.append(KnowledgeChunk(
                        id=f"sec:owasp:{item.get('id', item.get('rank', 'x'))}",
                        text=f"{item.get('name', '')}\n{json.dumps(item)}",
                        source="security_knowledge_base",
                        domain="cybersecurity",
                        title=item.get("name", "OWASP entry"),
                        metadata={"framework": "OWASP", "raw": item},
                    ))
                for cwe in security.get_all_cwes():
                    chunks.append(KnowledgeChunk(
                        id=f"sec:cwe:{cwe.get('id', uuid.uuid4().hex[:6])}",
                        text=f"{cwe.get('id', '')} {cwe.get('name', '')}\n{cwe.get('description', '')}",
                        source="security_knowledge_base",
                        domain="cybersecurity",
                        title=f"{cwe.get('id', '')} {cwe.get('name', '')}",
                        metadata={"framework": "CWE", "raw": cwe},
                    ))
            except Exception as e:
                logger.debug(f"[KNOWLEDGE] security cache skipped: {e}")

        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT c.id, c.text, c.domain, c.metadata, d.title, d.source "
                    "FROM knowledge_chunks c JOIN knowledge_documents d ON d.id = c.document_id"
                ).fetchall()
            for row in rows:
                chunks.append(KnowledgeChunk(
                    id=row["id"], text=row["text"], source=row["source"] or "ingested_document",
                    domain=row["domain"] or "documents", title=row["title"] or "",
                    metadata=json.loads(row["metadata"] or "{}"),
                ))
        except Exception as e:
            logger.debug(f"[KNOWLEDGE] document cache skipped: {e}")

        self._chunk_cache = chunks
        self._idf = _compute_idf([_tokenize(c.text) for c in chunks])
        self._cache_built = True
        logger.info(f"[KNOWLEDGE] Retrieval corpus built: {len(chunks)} chunks, {len(self._idf)} terms")

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    def search(self, query: str, domain: str | None = None, limit: int = 8,
               min_score: float = 1.5) -> dict[str, Any]:
        self._build_cache()
        if not self._chunk_cache:
            return {"success": False, "error": "No knowledge corpora are available to search.",
                    "results": [], "query": query}

        query_tokens = _tokenize(query)
        if not query_tokens:
            return {"success": False, "error": "Query contained no searchable terms.",
                    "results": [], "query": query}

        # A query whose terms barely exist in the index cannot produce a real
        # match; refuse it up front instead of surfacing coincidental gibberish.
        self._build_cache()
        vocabulary = set(self._idf.keys())
        matched = [t for t in query_tokens if t in vocabulary]
        if len(matched) < min(2, len(query_tokens)):
            return {
                "success": False,
                "query": query,
                "domain_filter": domain,
                "results": [],
                "error": (
                    f"No knowledge retrieved for '{query}': only {len(matched)} of "
                    f"{len(query_tokens)} query terms exist in the indexed corpus "
                    f"({len(self._chunk_cache)} chunks). Ingest a relevant document or "
                    "rephrase the query — JARVIS does not invent an answer when "
                    "retrieval fails."
                ),
                "corpus_size": len(self._chunk_cache),
            }

        target_domain = _normalize_query_domain(domain, query) if domain or True else domain
        scored: list[KnowledgeChunk] = []
        for chunk in self._chunk_cache:
            if target_domain and chunk.domain != target_domain:
                continue
            score = _bm25_score(query_tokens, _tokenize(chunk.text), self._idf, len(self._chunk_cache))
            if chunk.title and any(t in chunk.title.lower() for t in query_tokens):
                score *= 1.6
            if score >= min_score:
                scored.append(KnowledgeChunk(**{**chunk.__dict__, "score": score}))

        if not scored and target_domain:
            # Retry without the domain restriction rather than returning nothing.
            for chunk in self._chunk_cache:
                score = _bm25_score(query_tokens, _tokenize(chunk.text), self._idf, len(self._chunk_cache))
                if score >= min_score:
                    scored.append(KnowledgeChunk(**{**chunk.__dict__, "score": score}))

        scored.sort(key=lambda c: c.score, reverse=True)
        top = scored[:limit]

        if not top:
            return {
                "success": False,
                "query": query,
                "domain_filter": target_domain,
                "results": [],
                "error": (
                    f"No knowledge retrieved for '{query}'. "
                    f"{len(self._chunk_cache)} chunks are indexed"
                    + (f" in domain '{target_domain}'" if target_domain else "")
                    + ". Ingest a relevant document or rephrase the query — "
                      "JARVIS does not invent an answer when retrieval fails."
                ),
                "corpus_size": len(self._chunk_cache),
            }

        return {
            "success": True,
            "query": query,
            "domain_filter": target_domain,
            "result_count": len(top),
            "corpus_size": len(self._chunk_cache),
            "results": [c.to_dict() for c in top],
            "sources": sorted({c.source for c in top}),
        }

    def answer_context(self, query: str, domain: str | None = None, limit: int = 5) -> dict[str, Any]:
        """Retrieval result shaped for an LLM prompt, with source attribution."""
        result = self.search(query, domain=domain, limit=limit)
        if not result.get("success"):
            return result
        context = "\n\n".join(
            f"[{i + 1}] ({item['source']} / {item['domain']}) {item['title']}\n{item['text'][:1200]}"
            for i, item in enumerate(result["results"])
        )
        return {
            "success": True,
            "query": query,
            "context": context,
            "citations": [
                {"index": i + 1, "source": item["source"], "domain": item["domain"],
                 "title": item["title"], "score": item["score"]}
                for i, item in enumerate(result["results"])
            ],
        }

    def domains(self) -> dict[str, Any]:
        self._build_cache()
        counts: dict[str, int] = {}
        sources: dict[str, int] = {}
        for chunk in self._chunk_cache:
            counts[chunk.domain] = counts.get(chunk.domain, 0) + 1
            sources[chunk.source] = sources.get(chunk.source, 0) + 1
        return {"domains": counts, "sources": sources, "total_chunks": len(self._chunk_cache),
                "canonical_domains": sorted(DOMAIN_ALIASES.keys())}

    def get_status(self) -> dict[str, Any]:
        self._build_cache()
        return {
            "corpus_chunks": len(self._chunk_cache),
            "vocabulary": len(self._idf),
            "retrieval": "lexical BM25 (vector pass available when sentence-transformers is installed)",
            "robotics_corpus": bool(self._load_robotics()),
            "indic_corpus": bool(self._load_indian()),
            "security_corpus": bool(self._load_security()),
            "ingested_documents": len(self.list_documents()),
            "vector_available": _vector_available(),
        }


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            while len(paragraph) > chunk_size:
                chunks.append(paragraph[:chunk_size])
                paragraph = paragraph[chunk_size - overlap:]
            current = paragraph
    if current:
        chunks.append(current)
    if not chunks and text.strip():
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), max(1, chunk_size - overlap))]
    return chunks


def _compute_idf(token_lists: list[list[str]]) -> dict[str, float]:
    total = len(token_lists) or 1
    doc_freq: Counter = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))
    return {term: math.log((total - freq + 0.5) / (freq + 0.5) + 1.0)
            for term, freq in doc_freq.items()}


def _bm25_score(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float],
                corpus_size: int, k1: float = 1.5, b: float = 0.75) -> float:
    if not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    avg_len = 200.0
    counts = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        freq = counts.get(token, 0)
        if freq == 0:
            continue
        term_idf = idf.get(token, math.log(corpus_size + 1))
        denominator = freq + k1 * (1 - b + b * doc_len / avg_len)
        score += term_idf * (freq * (k1 + 1)) / denominator
    return score


def _normalize_domain(domain_name: str, tags: list[str]) -> str:
    haystack = " ".join([domain_name] + (tags or [])).lower()
    for canonical, keywords in DOMAIN_ALIASES.items():
        if any(keyword in haystack for keyword in keywords):
            return canonical
    return domain_name.lower()


def _normalize_query_domain(domain: str | None, query: str) -> str | None:
    if domain:
        domain = domain.lower()
        if domain in DOMAIN_ALIASES:
            return domain
        for canonical, keywords in DOMAIN_ALIASES.items():
            if domain in keywords:
                return canonical
        return domain
    query_lower = query.lower()
    for canonical, keywords in DOMAIN_ALIASES.items():
        if any(keyword in query_lower for keyword in keywords):
            return canonical
    return None


def _vector_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


_kb: UnifiedKnowledgeBase | None = None


def get_knowledge_base() -> UnifiedKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = UnifiedKnowledgeBase()
    return _kb
