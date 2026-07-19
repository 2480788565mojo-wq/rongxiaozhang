import json
from pathlib import Path
from typing import Any

from app.rag.chroma_store import get_finance_collection


SEED_FILE = Path(__file__).parent / "seed_data" / "finance_tips.jsonl"


def load_seed_tips(path: Path = SEED_FILE) -> list[dict[str, Any]]:
    tips: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not item.get("category") or not item.get("content"):
                raise ValueError(f"种子知识第 {line_number} 行缺少分类或内容")
            tips.append(item)
    return tips


def seed_finance_tips(tips: list[dict[str, Any]] | None = None) -> int:
    collection = get_finance_collection()
    if collection.count() > 0:
        return 0

    source = tips if tips is not None else load_seed_tips()
    if not source:
        return 0
    collection.add(
        ids=[f"tip_{index:04d}" for index in range(len(source))],
        documents=[item["content"] for item in source],
        metadatas=[
            {
                "category": item["category"],
                "source": item.get("source", "荣小账知识库"),
            }
            for item in source
        ],
    )
    return len(source)


def retrieve_relevant_tips(query: str, top_k: int = 5) -> list[str]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []
    collection = get_finance_collection()
    if collection.count() == 0:
        seed_finance_tips()
    result = collection.query(
        query_texts=[cleaned_query],
        n_results=max(1, min(top_k, 20)),
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents") or [[]]
    return list(documents[0])
