"""Reproducible RAG recall evaluation for the finance_tips collection.

Usage:
    cd backend
    .\\.venv_clean\\Scripts\\python.exe ..\\loadtest\\rag_eval.py

The embedding model is read from the local HuggingFace cache; no network is
required once the model has been downloaded.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

for _proxy in (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
):
    os.environ.pop(_proxy, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
# This workspace's model cache lives outside the default user cache.
_cache = Path(r"D:\cache\huggingface")
if _cache.exists():
    os.environ["HF_HOME"] = str(_cache)
    os.environ["HF_HUB_CACHE"] = str(_cache / "hub")

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.rag.retriever import (  # noqa: E402
    get_finance_collection,
    load_seed_tips,
    seed_finance_tips,
)

QUERY_FILE = Path(__file__).parent / "rag_queries.jsonl"
OUTPUT_FILE = Path(__file__).parent / "rag_eval_results.json"
K_VALUES = (1, 3, 5)


def load_queries() -> list[dict]:
    queries = []
    with QUERY_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                queries.append(json.loads(line))
    return queries


def evaluate_one(collection, item: dict) -> dict:
    result = collection.query(
        query_texts=[item["query"]],
        n_results=max(K_VALUES),
        include=["documents", "metadatas", "distances"],
    )
    ids = list((result.get("ids") or [[]])[0])
    documents = list((result.get("documents") or [[]])[0])
    distances = list((result.get("distances") or [[]])[0])
    gold = set(item["relevant"])
    ranks = [index + 1 for index, doc_id in enumerate(ids) if doc_id in gold]
    metrics = {}
    for k in K_VALUES:
        top = ids[:k]
        recall = len(gold.intersection(top)) / len(gold) if gold else None
        hit = 1 if gold.intersection(top) else 0
        metrics[f"recall@{k}"] = recall
        metrics[f"hit@{k}"] = hit
    metrics["mrr@5"] = 1 / ranks[0] if ranks else 0.0
    metrics["false_positive@3"] = (
        None if gold else (1 if ids[:3] else 0)
    )
    return {
        "id": item["id"],
        "type": item["type"],
        "query": item["query"],
        "relevant": item["relevant"],
        "retrieved": [
            {"id": doc_id, "distance": round(float(distance), 4), "document": document}
            for doc_id, distance, document in zip(ids, distances, documents)
        ],
        "metrics": metrics,
    }


def mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4) if values else 0.0


def main() -> None:
    collection = get_finance_collection()
    if collection.count() == 0:
        seed_finance_tips(load_seed_tips())
    print(f"collection_count={collection.count()}")
    print(f"embedding_model=BAAI/bge-small-zh-v1.5")
    print(f"index=chroma_hnsw_cosine topK={max(K_VALUES)}")

    queries = load_queries()
    records = [evaluate_one(collection, item) for item in queries]

    by_type: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_type[record["type"]].append(record)

    summary = {}
    positive = [r for r in records if r["relevant"]]
    for label, subset in [("overall_positive", positive), *by_type.items()]:
        if not subset or all(r["metrics"]["recall@1"] is None for r in subset):
            summary[label] = {
                "count": len(subset),
                "note": "negative/unanswerable queries; see false_positive@3",
                "false_positive@3": mean([
                    r["metrics"]["false_positive@3"] or 0 for r in subset
                ]),
            }
            continue
        summary[label] = {
            "count": len(subset),
            "recall@1": mean([r["metrics"]["recall@1"] for r in subset]),
            "recall@3": mean([r["metrics"]["recall@3"] for r in subset]),
            "recall@5": mean([r["metrics"]["recall@5"] for r in subset]),
            "hit@1": mean([r["metrics"]["hit@1"] for r in subset]),
            "hit@3": mean([r["metrics"]["hit@3"] for r in subset]),
            "hit@5": mean([r["metrics"]["hit@5"] for r in subset]),
            "mrr@5": mean([r["metrics"]["mrr@5"] for r in subset]),
        }

    output = {
        "dataset": {
            "file": str(QUERY_FILE.name),
            "queries": len(queries),
            "positive": len(positive),
            "negative": len(queries) - len(positive),
            "k_values": list(K_VALUES),
            "label_rule": "文档内容直接回答查询或提供其关键建议；多跳查询需两个相关文档都计入 gold",
        },
        "config": {
            "collection": "finance_tips",
            "documents": collection.count(),
            "embedding_model": "BAAI/bge-small-zh-v1.5",
            "embedding_dim": 512,
            "normalize_embeddings": True,
            "index": "Chroma HNSW cosine",
            "chunking": "每条知识一个 chunk（无二次切分/重叠）",
            "top_k_evaluated": list(K_VALUES),
            "production_top_k": 3,
            "filter": "无元数据过滤",
        },
        "summary": summary,
        "queries": records,
    }
    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nsummary")
    for label, values in summary.items():
        print(label, json.dumps(values, ensure_ascii=False))
    print(f"\nwrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
