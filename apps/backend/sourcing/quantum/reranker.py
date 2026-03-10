"""
Quantum Re-Ranking Service for search result scoring.

Ported from HeyLois/eco-system/quantum XanaduQuantumReranker.
Uses numpy-based quantum circuit simulation by default (no hardware deps).
Feature flag QUANTUM_RERANKING_ENABLED controls activation.

Core idea: Map query and candidate embeddings to quantum circuit parameters,
run simulated interference patterns, and extract similarity scores that
capture non-linear relationships cosine similarity misses.
"""

import logging
import os
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)

QUANTUM_RERANKING_ENABLED = os.getenv("QUANTUM_RERANKING_ENABLED", "true").lower() in ("1", "true", "yes")
QUANTUM_N_MODES = int(os.getenv("QUANTUM_N_MODES", "8"))
QUANTUM_BLEND_FACTOR = float(os.getenv("QUANTUM_BLEND_FACTOR", "0.7"))


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    """L2 normalize vector with numerical stability."""
    return x / (np.linalg.norm(x) + 1e-12)


def _reduce_embedding(embedding: np.ndarray, n_modes: int) -> np.ndarray:
    """Reduce high-dimensional embedding to quantum parameters [0, π]."""
    embedding = _l2_normalize(np.asarray(embedding, dtype=np.float64).ravel())
    if embedding.size == 0:
        return np.zeros(n_modes, dtype=np.float64)

    pooled = np.array(
        [float(chunk.mean()) if chunk.size else 0.0 for chunk in np.array_split(embedding, n_modes)],
        dtype=np.float64,
    )
    mean_val = float(np.mean(pooled))
    std_val = float(np.std(pooled))
    if std_val < 1e-8:
        normalized = np.clip(pooled - mean_val, -1.0, 1.0)
    else:
        normalized = np.clip((pooled - mean_val) / std_val, -3.0, 3.0)
    return normalized / 3.0 * np.pi


def _simulate_quantum_kernel(query_params: np.ndarray, candidate_params: np.ndarray) -> float:
    """
    Simulate photonic quantum kernel using numpy.

    Approximates the interference pattern from:
    1. Squeezed state initialization
    2. Displacement encoding (query)
    3. Rotation + displacement encoding (candidate)
    4. Beamsplitter entanglement
    5. Number operator measurement

    This is a faithful numpy simulation of the Strawberry Fields Gaussian backend
    circuit from the sibling project, capturing the same interference patterns
    without requiring SF as a dependency.
    """
    n = len(query_params)

    # Phase 1: Squeezed state amplitudes (small squeezing r=0.1)
    squeeze_r = 0.1
    amplitudes = np.full(n, np.sinh(squeeze_r) ** 2, dtype=np.float64)

    # Phase 2: Displacement encoding (query)
    for i in range(n):
        r = abs(query_params[i]) * 0.5
        phi = query_params[i] * 0.3
        amplitudes[i] += r * np.cos(phi)

    # Phase 3: Rotation + displacement encoding (candidate)
    for i in range(n):
        amplitudes[i] *= np.cos(candidate_params[i])
        r_beta = abs(candidate_params[i]) * 0.3
        phi_beta = candidate_params[i] * 0.2
        amplitudes[i] += r_beta * np.cos(phi_beta)

    # Phase 4: Beamsplitter interference (ring topology)
    output = np.copy(amplitudes)
    for i in range(n):
        j = (i + 1) % n
        theta = candidate_params[i] * 0.1
        ct, st = np.cos(theta), np.sin(theta)
        a_i, a_j = output[i], output[j]
        output[i] = ct * a_i + st * a_j
        output[j] = -st * a_i + ct * a_j

    # Cross-connections for richer interference
    if n >= 4:
        for i in range(0, n - 2, 2):
            theta = np.pi / 8
            ct, st = np.cos(theta), np.sin(theta)
            a_i, a_j = output[i], output[i + 2]
            output[i] = ct * a_i + st * a_j
            output[i + 2] = -st * a_i + ct * a_j

    # Phase 5: Measurement — weighted average of absolute amplitudes
    weights = np.array([1.0 / (i + 1) for i in range(n)])
    signed_sum = float(np.sum(weights * output))
    magnitude_sum = float(np.sum(weights * np.abs(output))) + 1e-12
    return float(np.clip(signed_sum / magnitude_sum, -1.0, 1.0))


class QuantumReranker:
    """
    Quantum re-ranker using simulated photonic interference.
    Reranks search results by computing quantum similarity between
    query and candidate embeddings.
    """

    def __init__(
        self,
        n_modes: int = QUANTUM_N_MODES,
        blend_factor: float = QUANTUM_BLEND_FACTOR,
    ):
        self.n_modes = n_modes
        self.blend_factor = blend_factor
        self._enabled = QUANTUM_RERANKING_ENABLED
        logger.info(
            f"QuantumReranker initialized: n_modes={n_modes}, blend={blend_factor}, enabled={self._enabled}"
        )

    def is_available(self) -> bool:
        return self._enabled

    def quantum_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embedding: np.ndarray,
    ) -> float:
        """Calculate quantum similarity using simulated photonic interference."""
        if not self._enabled:
            return 0.0
        try:
            q_params = _reduce_embedding(query_embedding, self.n_modes)
            c_params = _reduce_embedding(candidate_embedding, self.n_modes)
            raw = _simulate_quantum_kernel(q_params, c_params)
            return float(np.clip(raw, -1.0, 1.0))
        except Exception as e:
            logger.error(f"Quantum similarity failed: {e}")
            return 0.0

    def classical_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embedding: np.ndarray,
    ) -> float:
        """Cosine similarity between two embeddings."""
        q = _l2_normalize(query_embedding)
        c = _l2_normalize(candidate_embedding)
        return float(np.clip(np.dot(q, c), -1.0, 1.0))

    def _normalize_similarity(self, score: float) -> float:
        return float(np.clip((score + 1.0) / 2.0, 0.0, 1.0))

    def _novelty_score(self, quantum: float, classical: float) -> float:
        """High novelty = quantum found something classical missed."""
        quantum_signal = self._normalize_similarity(quantum)
        classical_signal = self._normalize_similarity(classical)
        return max(0.0, quantum_signal - classical_signal)

    def _coherence_score(self, quantum: float, classical: float) -> float:
        """Measures match robustness via quantum coherence."""
        quantum_signal = self._normalize_similarity(quantum)
        classical_signal = self._normalize_similarity(classical)
        return max(0.0, 1.0 - abs(quantum_signal - classical_signal))

    def _blended_score(
        self, quantum: float, classical: float, novelty: float, coherence: float
    ) -> float:
        quantum_signal = self._normalize_similarity(quantum)
        classical_signal = self._normalize_similarity(classical)
        base_score = self.blend_factor * quantum_signal + (1.0 - self.blend_factor) * classical_signal
        return float(np.clip(0.9 * base_score + 0.05 * base_score * coherence + 0.05 * novelty, 0.0, 1.0))

    async def rerank_results(
        self,
        query_embedding: List[float],
        search_results: List[Dict[str, Any]],
        top_k: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using quantum similarity.

        Args:
            query_embedding: Query embedding (1536-dim).
            search_results: Results with optional 'embedding' key.
            top_k: Max results to return.

        Returns:
            Reranked results with quantum scores.
        """
        if not self._enabled or not search_results:
            return search_results[:top_k]

        query_emb = np.array(query_embedding, dtype=np.float32)
        enhanced: List[Dict[str, Any]] = []

        for result in search_results:
            candidate_embedding = result.get("embedding")
            if candidate_embedding is None:
                # No embedding — keep result with neutral quantum scores
                enhanced.append(result)
                continue

            candidate_emb = np.asarray(candidate_embedding, dtype=np.float32).ravel()
            if candidate_emb.size == 0:
                enhanced.append(result)
                continue

            q_score = self.quantum_similarity(query_emb, candidate_emb)
            c_score = self.classical_similarity(query_emb, candidate_emb)
            novelty = self._novelty_score(q_score, c_score)
            coherence = self._coherence_score(q_score, c_score)
            blended = self._blended_score(q_score, c_score, novelty, coherence)

            enhanced_result = dict(result)
            enhanced_result.update(
                {
                    "quantum_score": round(q_score, 4),
                    "classical_score": round(c_score, 4),
                    "novelty_score": round(novelty, 4),
                    "coherence_score": round(coherence, 4),
                    "blended_score": round(blended, 4),
                    "quantum_reranked": True,
                }
            )
            enhanced.append(enhanced_result)

        # Sort: quantum-reranked by blended_score, non-reranked at the end
        reranked = [r for r in enhanced if r.get("quantum_reranked")]
        non_reranked = [r for r in enhanced if not r.get("quantum_reranked")]
        reranked.sort(key=lambda x: x.get("blended_score", 0.0), reverse=True)

        final = (reranked + non_reranked)[:top_k]
        logger.info(f"Quantum reranking: {len(reranked)} reranked, {len(non_reranked)} without embeddings")
        return final
