import json

import retrieval.retriever as retriever_mod
from retrieval.retriever import Chunk, _extract_article_refs, _get_bm25_retriever


class TestExtractArticleRefs:
    def test_stattia_pattern(self) -> None:
        assert _extract_article_refs("стаття 17 закону") == {"article_number": "17"}

    def test_abbreviated_st(self) -> None:
        assert _extract_article_refs("ст. 22 ЗУ") == {"article_number": "22"}

    def test_abbreviated_st_no_dot(self) -> None:
        assert _extract_article_refs("ст 5 про закупівлі") == {"article_number": "5"}

    def test_no_match_returns_none(self) -> None:
        assert _extract_article_refs("загальне питання про тендер") is None

    def test_case_insensitive(self) -> None:
        assert _extract_article_refs("СТАТТЯ 5") == {"article_number": "5"}

    def test_returns_first_match(self) -> None:
        result = _extract_article_refs("стаття 17 і стаття 22")
        assert result == {"article_number": "17"}


class TestBM25TagFiltering:
    """BM25 retriever should restrict its corpus to documents whose tags overlap
    with the requested whitelist, keeping Qdrant and BM25 in sync."""

    def _write_jsonl(self, path, records: list[dict]) -> None:
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    def _make_records(self):
        return [
            {"text": "tutorial content", "tags": ["tutorial"], "id": "1", "doc_id": "d1"},
            {"text": "interface content", "tags": ["interface"], "id": "2", "doc_id": "d2"},
            {"text": "marketplace content", "tags": ["marketplace"], "id": "3", "doc_id": "d3"},
            {"text": "untagged content", "tags": [], "id": "4", "doc_id": "d4"},
            {"text": "string-tagged content", "tags": "tutorial", "id": "5", "doc_id": "d5"},
        ]

    def test_whitelist_filters_to_matching_tags(self, tmp_path, monkeypatch):
        jsonl = tmp_path / "articles.jsonl"
        self._write_jsonl(jsonl, self._make_records())
        monkeypatch.setattr(retriever_mod, "_COLLECTION_PATHS", {"articles": [jsonl]})
        retriever_mod._bm25_cache.clear()

        ret = _get_bm25_retriever("articles", tag_whitelist=["tutorial"])
        texts = {d.page_content for d in ret.docs}

        assert "tutorial content" in texts
        assert "string-tagged content" in texts  # string tag normalised to list
        assert "interface content" not in texts
        assert "untagged content" not in texts

    def test_multi_tag_whitelist(self, tmp_path, monkeypatch):
        jsonl = tmp_path / "articles.jsonl"
        self._write_jsonl(jsonl, self._make_records())
        monkeypatch.setattr(retriever_mod, "_COLLECTION_PATHS", {"articles": [jsonl]})
        retriever_mod._bm25_cache.clear()

        ret = _get_bm25_retriever("articles", tag_whitelist=["tutorial", "marketplace"])
        texts = {d.page_content for d in ret.docs}

        assert "tutorial content" in texts
        assert "marketplace content" in texts
        assert "interface content" not in texts

    def test_no_whitelist_returns_all_docs(self, tmp_path, monkeypatch):
        jsonl = tmp_path / "articles.jsonl"
        self._write_jsonl(jsonl, self._make_records())
        monkeypatch.setattr(retriever_mod, "_COLLECTION_PATHS", {"articles": [jsonl]})
        retriever_mod._bm25_cache.clear()

        ret = _get_bm25_retriever("articles", tag_whitelist=None)
        assert len(ret.docs) == 5

    def test_empty_match_falls_back_to_placeholder(self, tmp_path, monkeypatch):
        jsonl = tmp_path / "articles.jsonl"
        self._write_jsonl(jsonl, self._make_records())
        monkeypatch.setattr(retriever_mod, "_COLLECTION_PATHS", {"articles": [jsonl]})
        retriever_mod._bm25_cache.clear()

        # Must not raise even when no docs match the whitelist
        ret = _get_bm25_retriever("articles", tag_whitelist=["nonexistent_tag"])
        assert ret is not None
        assert len(ret.docs) == 1
        assert ret.docs[0].metadata.get("_placeholder") is True

    def test_different_whitelists_use_separate_cache_entries(self, tmp_path, monkeypatch):
        jsonl = tmp_path / "articles.jsonl"
        self._write_jsonl(jsonl, self._make_records())
        monkeypatch.setattr(retriever_mod, "_COLLECTION_PATHS", {"articles": [jsonl]})
        retriever_mod._bm25_cache.clear()

        ret_a = _get_bm25_retriever("articles", tag_whitelist=["tutorial"])
        ret_b = _get_bm25_retriever("articles", tag_whitelist=["interface"])
        ret_all = _get_bm25_retriever("articles")

        assert ret_a is not ret_b
        assert ret_a is not ret_all
        assert len(retriever_mod._bm25_cache) == 3


class TestHybridSearchTagExtraction:
    """hybrid_search extracts the tag whitelist from filters and passes it to BM25."""

    class _FakeRetriever:
        def invoke(self, query: str) -> list:
            return []

    def _patch_pipeline(self, monkeypatch) -> dict:
        """Replace the heavy pipeline components with no-op fakes.

        Returns a dict where captured["tag_whitelist"] is set by the fake BM25 factory.
        """
        captured: dict = {}

        def fake_bm25(collection, tag_whitelist=None):
            captured["tag_whitelist"] = tag_whitelist
            from langchain_community.retrievers import BM25Retriever
            from langchain_core.documents import Document
            ret = BM25Retriever.from_documents([Document(page_content="placeholder")])
            ret.k = 5
            return ret

        fake_ret = self._FakeRetriever()
        monkeypatch.setattr(retriever_mod, "_get_bm25_retriever", fake_bm25)
        monkeypatch.setattr(retriever_mod, "_get_reranker", lambda: None)
        monkeypatch.setattr(retriever_mod, "_QdrantRetriever", lambda **kw: fake_ret)
        monkeypatch.setattr(retriever_mod, "EnsembleRetriever", lambda **kw: fake_ret)
        monkeypatch.setattr(retriever_mod, "ContextualCompressionRetriever", lambda **kw: fake_ret)
        return captured

    def test_tag_whitelist_extracted_from_filters(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)

        retriever_mod.hybrid_search(
            "платформа не працює",
            collection="articles",
            filters={"tags": ["tutorial", "interface"]},
        )

        assert captured["tag_whitelist"] == ["tutorial", "interface"]

    def test_string_tag_normalised_to_list(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)

        retriever_mod.hybrid_search(
            "питання",
            collection="articles",
            filters={"tags": "tutorial"},
        )

        assert captured["tag_whitelist"] == ["tutorial"]

    def test_no_tags_in_filters_passes_none_to_bm25(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)

        retriever_mod.hybrid_search(
            "стаття 17",
            collection="laws",
            filters={"article_number": "17"},
        )

        assert captured["tag_whitelist"] is None

    def test_no_filters_passes_none_to_bm25(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)

        retriever_mod.hybrid_search(
            "загальне питання про тендер",
            collection="articles",
            filters=None,
        )

        assert captured["tag_whitelist"] is None


class TestChunkModel:
    def test_construction(self) -> None:
        chunk = Chunk(id="abc", doc_id="law-922", text="text", score=0.8, metadata={})
        assert chunk.score == 0.8
        assert chunk.text == "text"
        assert chunk.doc_id == "law-922"

    def test_empty_metadata(self) -> None:
        chunk = Chunk(id="x", doc_id="d", text="t", score=0.0, metadata={})
        assert chunk.metadata == {}

    def test_metadata_with_fields(self) -> None:
        meta = {"breadcrumb": "Закон 922 → Стаття 17", "version_date": "2024-01-01"}
        chunk = Chunk(id="y", doc_id="d", text="t", score=0.5, metadata=meta)
        assert chunk.metadata["breadcrumb"] == "Закон 922 → Стаття 17"
