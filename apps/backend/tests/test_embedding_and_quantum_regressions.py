import inspect
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from routes.rows_search import search_row_listings_stream
from sourcing.quantum.reranker import QuantumReranker, _reduce_embedding
from sourcing.service import SourcingService
from sourcing.vendor_provider import _build_embedding_concepts, build_query_embedding


class TestEmbeddingConcepts:
    def test_build_embedding_concepts_prefers_product_specs_and_context(self):
        concepts = _build_embedding_concepts(
            query="jet to nashville",
            context_query="private jet charter san diego to nashville",
            intent_payload={
                "product_name": "Private jet charter",
                "constraints": {
                    "origin": "San Diego",
                    "destination": "Nashville",
                },
                "keywords": ["private", "jet", "charter", "wifi"],
            },
        )

        assert concepts[0][0] == "Private jet charter"
        assert pytest.approx(sum(weight for _, weight in concepts), rel=1e-6) == 1.0
        assert any("San Diego" in text and "Nashville" in text for text, _ in concepts)
        assert any(text == "private jet charter san diego to nashville" for text, _ in concepts)

    @pytest.mark.asyncio
    async def test_build_query_embedding_reuses_precomputed_vector(self):
        precomputed = [0.25, 0.75]

        with patch("sourcing.vendor_provider._embed_texts", new=AsyncMock(side_effect=AssertionError("should not embed"))):
            result = await build_query_embedding(
                query="standing desk",
                context_query="standing desk under 600",
                pre_computed=precomputed,
            )

        assert result == precomputed

    @pytest.mark.asyncio
    async def test_build_query_embedding_batches_concepts_once_and_blends(self):
        embed_mock = AsyncMock(return_value=[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])

        with patch("sourcing.vendor_provider._embed_texts", new=embed_mock):
            result = await build_query_embedding(
                query="gift card",
                context_query="roblox gift card for birthday",
                intent_payload={
                    "product_name": "Roblox gift card",
                    "constraints": {"budget": "$50"},
                    "keywords": ["roblox", "gift", "card"],
                },
            )

        assert result is not None
        assert len(result) == 2
        assert embed_mock.await_count == 1
        called_texts = embed_mock.await_args.args[0]
        assert called_texts[0] == "Roblox gift card"
        assert any("$50" in text for text in called_texts)
        assert any(text == "roblox gift card for birthday" for text in called_texts)


class TestSourcingServiceForwarding:
    def test_search_and_persist_forwards_shared_embedding_contract(self):
        source = inspect.getsource(SourcingService.search_and_persist)

        assert "vendor_query=vendor_query" in source
        assert "intent_payload=intent_payload" in source
        assert "query_embedding=query_embedding" in source
        assert "await build_query_embedding(" in source

    def test_search_and_persist_only_builds_embedding_for_vendor_directory_scope(self):
        source = inspect.getsource(SourcingService.search_and_persist)

        assert 'if not selected_provider_ids or "vendor_directory" in selected_provider_ids:' in source
        assert 'selected_provider_ids = normalizer(raw_provider_ids)' in source

    def test_stream_path_uses_shared_embedding_builder(self):
        source = inspect.getsource(search_row_listings_stream)

        assert "from sourcing.vendor_provider import build_query_embedding" in source
        assert "query_embedding = await build_query_embedding(" in source
        assert "intent_payload=intent_payload" in source


class TestQuantumRerankerRegressions:
    def test_reduce_embedding_uses_full_vector_signal_beyond_first_modes(self):
        embedding = np.array([0.0] * 8 + [1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0], dtype=np.float64)

        reduced = _reduce_embedding(embedding, n_modes=8)

        assert reduced.shape == (8,)
        assert np.any(np.abs(reduced) > 1e-6)

    def test_classical_similarity_preserves_negative_signal(self):
        reranker = QuantumReranker()

        score = reranker.classical_similarity(
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([-1.0, 0.0], dtype=np.float32),
        )

        assert score == pytest.approx(-1.0)

    @pytest.mark.asyncio
    async def test_rerank_results_skips_missing_and_empty_embeddings(self):
        reranker = QuantumReranker()

        results = await reranker.rerank_results(
            query_embedding=[1.0, 0.0],
            search_results=[
                {"title": "Missing", "embedding": None},
                {"title": "Empty", "embedding": []},
                {"title": "Valid", "embedding": [1.0, 0.0]},
            ],
            top_k=3,
        )

        assert len(results) == 3
        assert any(result.get("title") == "Valid" and result.get("quantum_reranked") for result in results)
        assert any(result.get("title") == "Missing" and not result.get("quantum_reranked") for result in results)
        assert any(result.get("title") == "Empty" and not result.get("quantum_reranked") for result in results)
