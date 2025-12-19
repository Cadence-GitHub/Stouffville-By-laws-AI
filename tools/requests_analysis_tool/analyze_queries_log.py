#!/usr/bin/env python3
"""
Query Log Analyzer (Two-Phase)

This tool reads a Town of Whitchurch-Stouffville `queries_log.json` file, analyses each
conversation entry and enriches it with additional, structured metadata. The resulting
output is written to `<INPUT_FILE>.analysis.json`.

The process is split into two phases:

1.  **Initial Processing (Default):**
    - Reads new entries from the input log.
    - Performs all analysis that does NOT require an LLM (embeddings, clustering,
      heuristics, performance metrics).
    - Creates the output file with the correct structure, setting LLM-dependent
      fields to `null`. This is done in one pass.

2.  **LLM Enrichment (with --fill-llm-fields):**
    - Reads the existing `.analysis.json` file.
    - Finds entries where LLM fields are `null`.
    - Calls the LLMs to fill in the missing data (category and evaluation).
    - Saves progress after each entry, making the process resumable.

Usage examples:
    # Phase 1: Create the analysis file with non-LLM data
    python tools/analyze_queries_log.py --input backend/queries_log.json

    # Phase 2: Fill in the missing LLM data
    python tools/analyze_queries_log.py --input backend/queries_log.json --fill-llm-fields

Environment variables expected:
    GOOGLE_API_KEY   – for Gemini
    VOYAGE_API_KEY   – for Voyage embeddings
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Third-party imports ---------------------------------------------------------
try:
    from langchain_voyageai import VoyageAIEmbeddings  # Embeddings
except ImportError:  # pragma: no cover
    VoyageAIEmbeddings = None  # type: ignore

try:
    from sklearn.cluster import DBSCAN  # Clustering
except ImportError:  # pragma: no cover
    DBSCAN = None  # type: ignore

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema.output_parser import StrOutputParser
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None  # type: ignore

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def load_json(fp: str) -> List[Dict[str, Any]]:
    """Load file expecting a list at top level."""
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON root is not a list")
        return data
    except Exception as exc:
        LOGGER.error("Failed to read JSON %s: %s", fp, exc)
        sys.exit(1)


def write_json(fp: str, obj: Dict[str, Any]) -> None:
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


BYLAW_REGEX = re.compile(r"(\d{4}-\d{3})")


def extract_bylaws(text: str) -> List[str]:
    return list({m.group(1) for m in BYLAW_REGEX.finditer(text or "")})


# ---------------------------------------------------------------------------
# Embedding cache utilities
# ---------------------------------------------------------------------------

def load_embedding_cache(path: Path) -> Dict[str, List[float]]:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            LOGGER.warning("Failed to load embedding cache %s: %s (starting fresh)", path, exc)
    return {}


def save_embedding_cache(path: Path, cache: Dict[str, List[float]]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception as exc:
        LOGGER.warning("Failed to save embedding cache to %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Cluster cache utilities
# ---------------------------------------------------------------------------

def load_cluster_cache(path: Path) -> Dict[str, Optional[str]]:
    """Return mapping query_text -> group_id (or None)."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            LOGGER.warning("Failed to load cluster cache %s: %s (recomputing)", path, exc)
    return {}


def save_cluster_cache(path: Path, cache: Dict[str, Optional[str]]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception as exc:
        LOGGER.warning("Failed to save cluster cache to %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Embeddings & clustering
# ---------------------------------------------------------------------------

def embed_all(queries: List[str], cache: Dict[str, List[float]], emb_fn) -> List[List[float]]:
    """Return embedding vectors for queries, using disk cache to avoid recomputation."""
    if emb_fn is None:
        LOGGER.error("Embedding function not initialised – VoyageAIEmbeddings unavailable.")
        sys.exit(1)

    seen = set()
    new_queries = []
    for q in queries:
        if q not in cache and q not in seen:
            seen.add(q)
            new_queries.append(q)

    if new_queries:
        LOGGER.info("Embedding %d queries (%d unique new) with Voyage-3-lite…", len(queries), len(new_queries))
        try:
            new_vecs = emb_fn.embed_documents(new_queries)
        except Exception as exc:
            LOGGER.error("Voyage embeddings failed: %s", exc)
            sys.exit(1)
        for q, vec in zip(new_queries, new_vecs):
            cache[q] = vec
        LOGGER.info("Embeddings ready. Total cached vectors: %d", len(cache))
    return [cache[q] for q in queries]


def cluster(vecs: List[List[float]], eps: float = 0.15, min_samples: int = 2) -> List[int]:
    if DBSCAN is None:
        LOGGER.error("scikit-learn not installed; clustering unavailable. Exiting.")
        sys.exit(1)
    if not vecs:
        return []
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    return model.fit_predict(vecs).tolist()


# ---------------------------------------------------------------------------
# LangChain LLM chains
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Animal Control", "Building & Construction", "Business Licensing", "Cannabis & Smoking",
    "Election Campaign", "Environmental Protection", "Fencing", "Fire & Fireworks", "Noise",
    "Parking & Traffic", "Parks & Recreation", "Property Standards", "Public Nuisance",
    "Signs & Advertising", "Snow & Ice", "Stormwater & Drainage", "Swimming Pools",
    "Trees & Forestry", "Waste Management", "Water & Sewer", "Zoning & Land Use", "Other",
]

CATEGORY_PROMPT = ChatPromptTemplate.from_template(
    f"""
You are a helpful assistant who categorises user questions about municipal bylaws.
Choose exactly one category from: {{categories}}.
Respond with the category only.
Query: "{{query}}"
"""
).partial(categories=", ".join(CATEGORIES))

EVAL_PROMPT = ChatPromptTemplate.from_template(
    """You are an expert evaluator for a municipal bylaw AI assistant serving the Town of Whitchurch-Stouffville. 

Your task is to evaluate the quality of AI responses to citizen questions about municipal bylaws. Return ONLY a valid JSON object with these exact keys:

{{
  "query_clarity_score": <1-5 integer>,
  "answer_correctness_score": <1-5 integer>,
  "answer_clarity_score": <1-5 integer>,
  "summary_quality_score": <1-5 integer>,
  "hallucination_flag": <true/false>,
  "query_language": "<language name>",
  "query_and_response_language_match": <true/false>
}}

EVALUATION CRITERIA:

1. **query_clarity_score (1-5)**: How clear and actionable is the user's question?
   - 5: Highly specific, well-structured, provides context
   - 4: Clear and specific with minor ambiguities
   - 3: Moderately clear but lacks some specificity
   - 2: Vague or ambiguous, requires clarification
   - 1: Very unclear, poorly structured, or incomprehensible

2. **answer_correctness_score (1-5)**: How accurate and relevant is the AI's response?
   - 5: Completely accurate, cites correct bylaws, addresses all aspects
   - 4: Mostly accurate with minor gaps or irrelevant details
   - 3: Generally accurate but missing some key information
   - 2: Partially accurate but contains errors or omissions
   - 1: Inaccurate, misleading, or completely irrelevant

3. **answer_clarity_score (1-5)**: How well-structured and understandable is the response?
   - 5: Exceptionally clear, well-organized, easy to follow
   - 4: Clear and well-structured with minor issues
   - 3: Generally clear but could be better organized
   - 2: Somewhat unclear or poorly structured
   - 1: Confusing, disorganized, or difficult to understand

4. **summary_quality_score (1-5)**: How well does the layman's answer summarize the technical response?
   - 5: Perfect summary, accessible language, captures all key points
   - 4: Good summary with minor omissions or clarity issues
   - 3: Adequate summary but misses some important details
   - 2: Poor summary, significant omissions or unclear language
   - 1: Inadequate summary, misleading or unhelpful

5. **hallucination_flag (true/false)**: Does the response contain false information?
   - true: Response contains factual errors, non-existent bylaws, or fabricated information
   - false: Response is factually accurate based on provided context

6. **query_language (string)**: What language is the user's query written in?
   - Identify the primary language of the query (e.g., "English", "French", "Spanish", "Mixed")
   - Use "Mixed" if the query contains multiple languages
   - Use "Unknown" if the language cannot be determined

7. **query_and_response_language_match (true/false)**: Do the query and response use the same language?
   - true: The response is provided in the same language as the query, OR if either the query or response contains mixed languages, at least one language is shared between them
   - false: The response language differs from the query language with no shared languages

CONTEXT TO ANALYZE:
- User Query: "{query}"
- Bylaws Cited in Answer: {cited_bylaws}
- Original Retrieved Bylaws: {original_bylaws}
- Additional Retrieved Bylaws: {additional_bylaws}
- Technical Answer: "{filtered_answer}"
- Layman Summary: "{laymans_answer}"

Focus on municipal bylaw accuracy, citizen accessibility, and practical usefulness. Consider whether the response helps a resident understand their obligations and rights under Whitchurch-Stouffville bylaws.

Return only the JSON object:"""
)


def init_llm(model: str) -> ChatGoogleGenerativeAI:  # type: ignore
    if ChatGoogleGenerativeAI is None:
        LOGGER.error("langchain_google_genai not installed. Exiting.")
        sys.exit(1)
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        LOGGER.error("GOOGLE_API_KEY env var not set. Exiting.")
        sys.exit(1)
    return ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.2)


# ---------------------------------------------------------------------------
# Basic heuristics
# ---------------------------------------------------------------------------

def query_complexity(q: str) -> str:
    words = len(q.split())
    if words < 10: return "Low"
    if words < 20: return "Medium"
    return "High"


def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb: return 1.0
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)


# ---------------------------------------------------------------------------
# Core Processing Logic
# ---------------------------------------------------------------------------

def update_slow_flags(analyzed_entries: List[Dict[str, Any]]):
    """Recompute p90 processing time and update is_slow_query flags in-place."""
    times = [e["analysis"].get("total_processing_time", 0) for e in analyzed_entries if e["analysis"].get("total_processing_time") is not None]
    if len(times) < 5:
        for e in analyzed_entries: e["analysis"]["is_slow_query"] = False
        return
    p90 = statistics.quantiles(times, n=10)[-1]
    for e in analyzed_entries:
        t = e["analysis"].get("total_processing_time")
        if t is not None: e["analysis"]["is_slow_query"] = t >= p90
    LOGGER.info("Updated slow query flags based on p90 processing time of %.2fs", p90)


def run_initial_processing(inp: Path, out_path: Path, args: argparse.Namespace):
    """Phase 1: Process new entries for non-LLM fields."""
    LOGGER.info("--- Starting Phase 1: Initial Processing ---")
    all_entries = load_json(str(inp))
    LOGGER.info("Total log entries in input: %d", len(all_entries))

    # Load / init output structure
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f: result = json.load(f)
            analyzed_entries = result.get("analyzed_entries", [])
            LOGGER.info("Loaded %d previously analyzed entries from %s", len(analyzed_entries), out_path)
        except Exception as exc:
            LOGGER.error("Failed to load existing analysis file %s: %s", out_path, exc)
            sys.exit(1)
    else:
        result = {
            "analysis_metadata": {
                "run_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_entries_processed": 0,
                "category_model_used": args.category_model,
                "eval_model_used": args.eval_model,
            },
            "analyzed_entries": [],
        }
        analyzed_entries = result["analyzed_entries"]

    processed_timestamps = {e["original_data"].get("timestamp") for e in analyzed_entries}
    to_process = [e for e in all_entries if e.get("timestamp") not in processed_timestamps]

    if not to_process:
        LOGGER.info("No new log entries to process. Exiting.")
        return

    LOGGER.info("%d new entries to process", len(to_process))

    # --- Handle Embeddings and Clustering ---
    emb_cache_path = Path(args.embeddings_cache) if args.embeddings_cache else inp.with_suffix(".embeddings.json")
    embedding_cache = load_embedding_cache(emb_cache_path)
    cluster_cache_path = Path(args.clusters_cache) if args.clusters_cache else inp.with_suffix(".clusters.json")
    cluster_map = load_cluster_cache(cluster_cache_path)

    if not cluster_map or any(q not in cluster_map for q in {e.get("query", "") for e in all_entries}):
        LOGGER.info("Recomputing clusters for all queries to ensure stable groups...")
        unique_queries = sorted({e.get("query", "") for e in all_entries})
        emb_fn = VoyageAIEmbeddings(model="voyage-3.5-lite") if VoyageAIEmbeddings else None
        _ = embed_all(unique_queries, embedding_cache, emb_fn)
        save_embedding_cache(emb_cache_path, embedding_cache)

        vectors_full = [embedding_cache[q] for q in unique_queries]
        labels_full = cluster(vectors_full)
        cluster_map = {q: (f"group_{lbl:04d}" if lbl != -1 else None) for q, lbl in zip(unique_queries, labels_full)}
        save_cluster_cache(cluster_cache_path, cluster_map)
        LOGGER.info("Cluster computation done. Saved to %s", cluster_cache_path)

    # --- Process new entries ---
    newly_analyzed = []
    for idx, entry in enumerate(to_process):
        analysis: Dict[str, Any] = {}
        q = entry.get("query", "")

        # Query metrics
        analysis["query_complexity"] = query_complexity(q)
        gid = cluster_map.get(q)
        analysis["query_group_id"] = gid

        # Duplicate detection (based on identical query text)
        all_processed_entries = analyzed_entries + newly_analyzed
        first_entry = next((e for e in all_processed_entries if e["original_data"].get("query", "") == q), None)
        analysis["is_duplicate_of"] = first_entry["original_data"].get("timestamp") if first_entry else None

        # Retrieval analysis
        cited = extract_bylaws(entry.get("filtered_answer", ""))
        orig = entry.get("original_bylaws", []) or []
        add = entry.get("additional_bylaws", []) or []
        analysis.update({
            "cited_bylaws_in_answer": cited,
            "retrieval_hit_original": bool(set(cited) & set(orig)),
            "retrieval_hit_transformed": bool(set(cited) & set(add)),
        })
        if analysis["retrieval_hit_transformed"]: impact = "Positive"
        else: impact = "Negative"
        analysis["transform_impact_on_cited_bylaws"] = impact

        # Performance metrics
        timings = entry.get("timings", {}) or {}
        tt = sum(timings.values())
        analysis["total_processing_time"] = round(tt, 3)
        analysis["bottleneck_component"] = max(timings, key=timings.get) if timings else None
        analysis["is_slow_query"] = False # Will be updated later

        # Set LLM fields to null
        analysis.update({
            "query_category": None,
            "query_clarity_score": None,
            "answer_correctness_score": None,
            "answer_clarity_score": None,
            "summary_quality_score": None,
            "hallucination_flag": None,
            "query_language": None,
            "query_and_response_language_match": None,
        })

        newly_analyzed.append({"original_data": entry, "analysis": analysis})
        LOGGER.info("Processed non-LLM data for entry %d/%d (timestamp: %s)", idx + 1, len(to_process), entry.get("timestamp"))

    # Append new entries to the main list
    analyzed_entries.extend(newly_analyzed)
    result["analysis_metadata"]["total_entries_processed"] = len(analyzed_entries)
    result["analysis_metadata"]["run_timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_slow_flags(analyzed_entries)

    write_json(str(out_path), result)
    LOGGER.info("Initial processing complete. Added %d new entries. Output saved to %s", len(newly_analyzed), out_path)


def run_llm_enrichment(out_path: Path, args: argparse.Namespace):
    """Phase 2: Fill in missing LLM data in an existing analysis file."""
    LOGGER.info("--- Starting Phase 2: LLM Enrichment ---")
    if not out_path.exists():
        LOGGER.error("Analysis file not found at %s. Please run the script without --fill-llm-fields first.", out_path)
        sys.exit(1)

    try:
        with open(out_path, "r", encoding="utf-8") as f: result = json.load(f)
        analyzed_entries = result.get("analyzed_entries", [])
        LOGGER.info("Loaded %d entries from %s", len(analyzed_entries), out_path)
    except Exception as exc:
        LOGGER.error("Failed to load analysis file %s: %s", out_path, exc)
        sys.exit(1)

    # Find entries that need LLM processing
    tasks = []
    for i, entry in enumerate(analyzed_entries):
        analysis = entry.get("analysis", {})
        needs_category = analysis.get("query_category") is None
        needs_eval = analysis.get("query_clarity_score") is None
        if needs_category or needs_eval:
            tasks.append({"index": i, "needs_category": needs_category, "needs_eval": needs_eval})

    if not tasks:
        LOGGER.info("No entries require LLM enrichment. All data is present.")
        return

    LOGGER.info("Found %d entries requiring LLM analysis.", len(tasks))

    # Initialise LLM chains
    category_llm = init_llm(args.category_model)
    eval_llm = init_llm(args.eval_model)
    category_chain = CATEGORY_PROMPT | category_llm | StrOutputParser()
    eval_chain = EVAL_PROMPT | eval_llm | StrOutputParser()

    for i, task in enumerate(tasks):
        entry_idx = task["index"]
        entry = analyzed_entries[entry_idx]
        analysis = entry["analysis"]
        original_data = entry["original_data"]
        q = original_data.get("query", "")
        ts = original_data.get("timestamp")

        LOGGER.info("Processing entry %d/%d (timestamp: %s)...", i + 1, len(tasks), ts)

        if task["needs_category"]:
            try:
                LOGGER.info("  - Calling Category LLM (%s)...", args.category_model)
                cat_result = category_chain.invoke({"query": q}).strip()
                analysis["query_category"] = cat_result
                LOGGER.info("  - Category received: %s", cat_result)
                time.sleep(2) # Rate limiting
            except Exception as exc:
                LOGGER.warning("  - Category LLM failed: %s. Setting to 'Other'.", exc)
                analysis["query_category"] = "Other"

        if task["needs_eval"]:
            cited = extract_bylaws(original_data.get("filtered_answer", ""))
            eval_inputs = {
                "query": q,
                "cited_bylaws": ", ".join(cited) or "None",
                "original_bylaws": ", ".join(original_data.get("original_bylaws", []) or []) or "None",
                "additional_bylaws": ", ".join(original_data.get("additional_bylaws", []) or []) or "None",
                "filtered_answer": original_data.get("filtered_answer", ""),
                "laymans_answer": original_data.get("laymans_answer", ""),
            }
            try:
                LOGGER.info("  - Calling Eval LLM (%s)...", args.eval_model)
                raw = eval_chain.invoke(eval_inputs)
                txt = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
                eval_data = json.loads(txt)
                analysis.update(eval_data)
                LOGGER.info("  - Evaluation scores received.")
                time.sleep(2) # Rate limiting
            except Exception as exc:
                LOGGER.warning("  - Eval LLM failed: %s. Setting scores to null.", exc)
                analysis.update({
                    "query_clarity_score": None, "answer_correctness_score": None,
                    "answer_clarity_score": None, "summary_quality_score": None,
                    "hallucination_flag": None, "query_language": None,
                    "query_and_response_language_match": None,
                })

        # Persist after each entry is updated
        result["analysis_metadata"]["run_timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        write_json(str(out_path), result)
        LOGGER.info("  - Saved progress for entry %s.", ts)

    LOGGER.info("LLM enrichment complete. Final output saved to %s", out_path)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    p = argparse.ArgumentParser(description="Analyse query log & enrich with metadata (two-phase & resumable)")
    p.add_argument("--input", "-i", required=True, help="Input queries_log.json path")
    p.add_argument("--output", "-o", help="Output analysis file (default <input>.analysis.json)")
    p.add_argument("--fill-llm-fields", action="store_true", help="Run LLM analysis on entries with null fields in the output file.")
    p.add_argument("--category-model", default="gemini-2.0-flash", help="Gemini model for categorisation")
    p.add_argument("--eval-model", default="gemini-2.5-flash", help="Gemini model for answer evaluation")
    p.add_argument("--google-api-key", "--api-key", dest="google_api_key", help="Google Gemini API key (overrides GOOGLE_API_KEY env)")
    p.add_argument("--voyage-api-key", dest="voyage_api_key", help="Voyage AI API key (overrides VOYAGE_API_KEY env)")
    p.add_argument("--embeddings-cache", help="Embeddings cache JSON file (default <input>.embeddings.json)")
    p.add_argument("--clusters-cache", help="Cluster mapping JSON file (default <input>.clusters.json)")
    args = p.parse_args()

    if args.google_api_key:
        os.environ["GOOGLE_API_KEY"] = args.google_api_key
        LOGGER.info("Using Google API key provided via command line")
    if args.voyage_api_key:
        os.environ["VOYAGE_API_KEY"] = args.voyage_api_key
        LOGGER.info("Using Voyage API key provided via command line")

    inp = Path(args.input)
    if not inp.exists():
        LOGGER.error("Input file not found %s", inp)
        return 1
    out_path = Path(args.output) if args.output else inp.with_suffix(".analysis.json")

    if args.fill_llm_fields:
        run_llm_enrichment(out_path, args)
    else:
        run_initial_processing(inp, out_path, args)

    return 0


if __name__ == "__main__":
    load_dotenv()
    sys.exit(main())
