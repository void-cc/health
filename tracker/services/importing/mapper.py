from typing import List, Optional, Tuple

from thefuzz import fuzz
from thefuzz import process as fuzz_process

from .candidates import ParsedMeasurementCandidate

CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.50


def _build_name_map() -> dict:
    """Build a dict mapping lowercase names/synonyms to MeasurementType instances."""
    from tracker.models import MeasurementType
    name_map: dict = {}
    for mt in MeasurementType.objects.all():
        name_map[mt.name.lower()] = mt
        for syn in (mt.synonyms or '').split(','):
            syn = syn.strip().lower()
            if syn:
                name_map[syn] = mt
    return name_map


def map_to_measurement_type(raw_name: str, name_map: dict, threshold: float = CONFIDENCE_THRESHOLD):
    """Fuzzy-match *raw_name* against *name_map*.

    Checks for an exact (case-insensitive) match first, then falls back to
    fuzzy ``ratio`` comparison.  Returns ``(MeasurementType | None, confidence_score)``
    where confidence is a float in [0, 1].
    """
    if not raw_name or not name_map:
        return None, 0.0

    normalized = raw_name.strip().lower()

    # Exact match shortcut
    if normalized in name_map:
        return name_map[normalized], 1.0

    keys = list(name_map.keys())
    best = fuzz_process.extractOne(normalized, keys, scorer=fuzz.ratio)
    if best is None:
        return None, 0.0

    score = best[1] / 100.0
    if score >= threshold:
        return name_map[best[0]], score
    return None, score


def map_candidates(
    candidates: List[ParsedMeasurementCandidate],
    threshold: float = CONFIDENCE_THRESHOLD,
) -> List[Tuple[ParsedMeasurementCandidate, Optional[object]]]:
    """Map each candidate to a MeasurementType using fuzzy matching.

    Updates ``candidate.confidence`` and ``candidate.measurement_type_name``
    in place.  Returns a list of ``(candidate, MeasurementType | None)`` tuples.
    """
    name_map = _build_name_map()
    results = []
    for cand in candidates:
        mt, score = map_to_measurement_type(cand.raw_name, name_map, threshold)
        cand.confidence = round(score, 4)
        if mt is not None:
            cand.measurement_type_name = mt.name
        results.append((cand, mt))
    return results
