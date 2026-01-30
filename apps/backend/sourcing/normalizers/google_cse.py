"""Google CSE normalizer."""

from __future__ import annotations

from typing import List

from sourcing.models import NormalizedResult
from sourcing.repository import SearchResult
from sourcing.normalizers import normalize_generic_results


def normalize_google_cse_results(results: List[SearchResult]) -> List[NormalizedResult]:
    return normalize_generic_results(results, "google_cse")
