"""Analytics service for computing lab insights, deltas, flags, and derived ratios."""

from django.db.models import QuerySet


def compute_delta(current_value, previous_value):
    """Return the absolute and percentage change between two values.

    Returns a dict with ``abs`` (absolute change), ``pct`` (percentage
    change as a float, e.g. 18.5 for +18.5 %), and ``direction``
    (``"up"``, ``"down"``, or ``"flat"``).
    """
    if previous_value is None or current_value is None:
        return None
    abs_change = current_value - previous_value
    if previous_value == 0:
        pct_change = 0.0
    else:
        pct_change = round((abs_change / abs(previous_value)) * 100, 1)
    if abs_change > 0:
        direction = "up"
    elif abs_change < 0:
        direction = "down"
    else:
        direction = "flat"
    return {"abs": round(abs_change, 2), "pct": pct_change, "direction": direction}


def is_out_of_range(value, ref_min, ref_max):
    """Return ``True`` when *value* falls outside [ref_min, ref_max].

    Returns ``None`` when reference bounds are not available.
    """
    if ref_min is None and ref_max is None:
        return None
    if ref_min is not None and value < ref_min:
        return True
    if ref_max is not None and value > ref_max:
        return True
    return False


def range_flag(value, ref_min, ref_max):
    """Return a human-readable flag: ``"low"``, ``"high"``, ``"normal"``, or ``None``."""
    if ref_min is None and ref_max is None:
        return None
    if ref_min is not None and value < ref_min:
        return "low"
    if ref_max is not None and value > ref_max:
        return "high"
    return "normal"


def compute_rolling_average(values, window=3):
    """Compute a simple rolling average over the last *window* values.

    *values* should be an iterable of numbers ordered oldest → newest.
    Returns the average of the last *window* entries, or ``None`` if
    fewer than *window* values are available.
    """
    vals = list(values)
    if len(vals) < window:
        return None
    subset = vals[-window:]
    return round(sum(subset) / len(subset), 2)


def compute_derived_ratios(latest_by_name):
    """Compute common derived lab ratios from a dict of ``{test_name: value}``.

    Currently supports:
    * **Total/HDL ratio** – ``Total Cholesterol / HDL``
    * **LDL/HDL ratio** – ``LDL / HDL``
    * **BUN/Creatinine ratio** – ``BUN / Creatinine``
    * **Neutrophil-Lymphocyte ratio (NLR)** – ``Neutrophils / Lymphocytes``

    Returns a list of dicts with ``name``, ``value``, and ``interpretation``.
    """
    ratios = []
    mapping = {k.lower(): v for k, v in latest_by_name.items()}

    # Total Cholesterol / HDL
    total_chol = mapping.get("total cholesterol") or mapping.get("cholesterol")
    hdl = mapping.get("hdl") or mapping.get("hdl cholesterol")
    if total_chol and hdl and hdl > 0:
        ratio_val = round(total_chol / hdl, 2)
        interp = "optimal" if ratio_val < 5 else "elevated"
        ratios.append({"name": "Total Cholesterol / HDL", "value": ratio_val, "interpretation": interp})

    # LDL / HDL
    ldl = mapping.get("ldl") or mapping.get("ldl cholesterol")
    if ldl and hdl and hdl > 0:
        ratio_val = round(ldl / hdl, 2)
        interp = "optimal" if ratio_val < 3.5 else "elevated"
        ratios.append({"name": "LDL / HDL", "value": ratio_val, "interpretation": interp})

    # BUN / Creatinine
    bun = mapping.get("bun") or mapping.get("blood urea nitrogen")
    creatinine = mapping.get("creatinine")
    if bun and creatinine and creatinine > 0:
        ratio_val = round(bun / creatinine, 1)
        if ratio_val < 10:
            interp = "low"
        elif ratio_val <= 20:
            interp = "normal"
        else:
            interp = "elevated"
        ratios.append({"name": "BUN / Creatinine", "value": ratio_val, "interpretation": interp})

    # Neutrophil-Lymphocyte Ratio
    neutrophils = mapping.get("neutrophils")
    lymphocytes = mapping.get("lymphocytes")
    if neutrophils and lymphocytes and lymphocytes > 0:
        ratio_val = round(neutrophils / lymphocytes, 2)
        interp = "normal" if ratio_val < 3 else "elevated"
        ratios.append({"name": "Neutrophil / Lymphocyte (NLR)", "value": ratio_val, "interpretation": interp})

    return ratios


def build_lab_insights(blood_tests_qs):
    """Build a list of insight summaries from a queryset of ``BloodTest`` objects.

    Each insight is a dict containing:

    * ``test_name``, ``latest_value``, ``unit``, ``date``
    * ``delta`` – result of :func:`compute_delta` vs the previous reading
    * ``flag`` – ``"low"`` / ``"high"`` / ``"normal"`` / ``None``
    * ``rolling_avg`` – 3-reading rolling average (or ``None``)

    The queryset is expected to be ordered ``-date`` (most recent first).
    """
    # Group tests by name preserving order (most recent first)
    by_name: dict[str, list] = {}
    for test in blood_tests_qs:
        by_name.setdefault(test.test_name, []).append(test)

    insights = []
    for name, tests in by_name.items():
        latest = tests[0]
        previous = tests[1] if len(tests) > 1 else None
        delta = compute_delta(latest.value, previous.value if previous else None)

        # Collect values oldest→newest for rolling average
        values_asc = [t.value for t in reversed(tests)]

        insights.append({
            "test_name": name,
            "latest_value": latest.value,
            "unit": latest.unit,
            "date": latest.date,
            "delta": delta,
            "flag": range_flag(latest.value, latest.normal_min, latest.normal_max),
            "normal_min": latest.normal_min,
            "normal_max": latest.normal_max,
            "rolling_avg": compute_rolling_average(values_asc, window=3),
        })

    return insights


def build_timeline_events(user, limit=30):
    """Assemble a chronological list of recent health events for *user*.

    Pulls from ``BloodTest``, ``VitalSign``, and ``Measurement`` models
    (importing inline to avoid circular imports at module level).
    Returns a list of dicts sorted newest-first, each with:
    ``type``, ``title``, ``date``, ``details``, ``badge`` (optional).
    """
    from tracker.models import BloodTest, VitalSign, Measurement

    events = []

    # Blood tests
    bt_qs = BloodTest.objects.filter(user=user).order_by("-date")[:limit]
    # Build lookup of previous values for delta computation
    all_bt = list(BloodTest.objects.filter(user=user).order_by("-date")[:200])
    prev_by_name: dict[str, float | None] = {}
    seen_latest: set[str] = set()
    for bt in all_bt:
        if bt.test_name not in seen_latest:
            seen_latest.add(bt.test_name)
        elif bt.test_name not in prev_by_name:
            prev_by_name[bt.test_name] = bt.value

    for bt in bt_qs:
        flag = range_flag(bt.value, bt.normal_min, bt.normal_max)
        delta = compute_delta(bt.value, prev_by_name.get(bt.test_name))
        badge = None
        detail_parts = [f"{bt.value} {bt.unit}"]
        if flag == "high":
            badge = "high"
            detail_parts.append("above range")
        elif flag == "low":
            badge = "low"
            detail_parts.append("below range")
        if delta:
            arrow = "↑" if delta["direction"] == "up" else ("↓" if delta["direction"] == "down" else "→")
            detail_parts.append(f"{arrow} {abs(delta['pct'])}% since last")
        events.append({
            "type": "blood_test",
            "title": bt.test_name,
            "date": bt.date,
            "details": " · ".join(detail_parts),
            "badge": badge,
        })

    # Vital signs
    vs_qs = VitalSign.objects.filter(user=user).order_by("-date")[:limit]
    for vs in vs_qs:
        parts = []
        if vs.heart_rate is not None:
            parts.append(f"HR {vs.heart_rate} bpm")
        if vs.systolic_bp is not None and vs.diastolic_bp is not None:
            parts.append(f"BP {vs.systolic_bp}/{vs.diastolic_bp}")
        if vs.weight is not None:
            parts.append(f"Weight {vs.weight} kg")
        if vs.spo2 is not None:
            parts.append(f"SpO₂ {vs.spo2}%")
        events.append({
            "type": "vital_sign",
            "title": "Vital Signs",
            "date": vs.date,
            "details": " · ".join(parts) if parts else "Recorded",
            "badge": None,
        })

    # Canonical Measurements (confirmed only)
    m_qs = Measurement.objects.filter(
        user=user, is_confirmed=True
    ).select_related("measurement_type").order_by("-observed_at")[:limit]
    for m in m_qs:
        flag = range_flag(m.value, m.ref_min, m.ref_max)
        badge = "high" if flag == "high" else ("low" if flag == "low" else None)
        events.append({
            "type": "measurement",
            "title": m.measurement_type.name,
            "date": m.observed_at.date() if hasattr(m.observed_at, "date") else m.observed_at,
            "details": f"{m.value} {m.unit}",
            "badge": badge,
        })

    # Sort all events newest first, limited
    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]
