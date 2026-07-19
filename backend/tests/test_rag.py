import sys

from app.rag.retriever import load_seed_tips, retrieve_relevant_tips


def test_seed_file_contains_fourteen_valid_tips():
    tips = load_seed_tips()

    assert len(tips) == 14
    assert all(item["category"] and item["content"] for item in tips)


def test_seed_file_covers_seven_finance_categories():
    categories = {item["category"] for item in load_seed_tips()}

    assert categories == {"餐饮", "交通", "购物", "居住", "储蓄", "信用卡", "保险"}


def test_empty_query_does_not_load_model():
    before = "sentence_transformers" in sys.modules

    assert retrieve_relevant_tips("   ") == []
    assert ("sentence_transformers" in sys.modules) is before
