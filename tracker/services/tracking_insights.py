"""Automated health insights engine for tracking data.

Provides trend analysis, anomaly detection, period comparisons, and
actionable health insights for each tracking module.
"""

from datetime import timedelta
from django.utils import timezone


def _trend_direction(values):
    """Return 'up', 'down', or 'stable' for a chronological list of numbers."""
    if len(values) < 2:
        return 'stable'
    first_half = values[:len(values) // 2]
    second_half = values[len(values) // 2:]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    diff_pct = ((avg_second - avg_first) / avg_first * 100) if avg_first else 0
    if diff_pct > 3:
        return 'up'
    elif diff_pct < -3:
        return 'down'
    return 'stable'


def _sparkline_points(values, width=60, height=20):
    """Generate SVG polyline points for a sparkline."""
    if len(values) < 2:
        return ''
    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min if v_max != v_min else 1
    n = len(values)
    pts = []
    for i, val in enumerate(values):
        x = round((i / (n - 1)) * (width - 4) + 2, 1)
        y = round((height - 2) - ((val - v_min) / v_range) * (height - 4), 1)
        pts.append(f'{x},{y}')
    return ' '.join(pts)


def _pct_change(old, new):
    if old is None or new is None or old == 0:
        return None
    return round(((new - old) / abs(old)) * 100, 1)


def body_composition_insights(queryset):
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {'has_data': True, 'alerts': [], 'tips': []}

    bf_values = [e.body_fat_percentage for e in entries if e.body_fat_percentage is not None]
    if bf_values:
        insights['body_fat_trend'] = _trend_direction(bf_values)
        insights['body_fat_sparkline'] = _sparkline_points(bf_values[-12:])
        insights['body_fat_current'] = bf_values[-1]
        if len(bf_values) >= 2:
            insights['body_fat_change'] = round(bf_values[-1] - bf_values[-2], 1)

    mm_values = [e.skeletal_muscle_mass for e in entries if e.skeletal_muscle_mass is not None]
    if mm_values:
        insights['muscle_trend'] = _trend_direction(mm_values)
        insights['muscle_sparkline'] = _sparkline_points(mm_values[-12:])
        insights['muscle_current'] = mm_values[-1]
        if len(mm_values) >= 2:
            insights['muscle_change'] = round(mm_values[-1] - mm_values[-2], 1)

    whr_values = [e.waist_to_hip_ratio for e in entries if e.waist_to_hip_ratio is not None]
    if whr_values:
        latest_whr = whr_values[-1]
        insights['whr_current'] = latest_whr
        if latest_whr > 0.95:
            insights['alerts'].append({
                'level': 'warning',
                'message': f'WHR of {latest_whr:.3f} indicates elevated cardiovascular risk.',
            })

    insights['entries_last_30'] = len(last_30)
    if len(last_30) < 2:
        insights['tips'].append('Log body composition at least twice a month for better trends.')

    return insights


def hydration_insights(queryset):
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_7 = [e for e in entries if e.date >= today - timedelta(days=7)]
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {'has_data': True, 'alerts': [], 'tips': []}

    intake_values = [e.fluid_intake_ml for e in entries if e.fluid_intake_ml is not None]
    if intake_values:
        insights['intake_sparkline'] = _sparkline_points(intake_values[-14:])
        insights['intake_trend'] = _trend_direction(intake_values[-14:])
        insights['avg_daily_intake'] = round(sum(intake_values[-7:]) / len(intake_values[-7:]))

    goal_met = [e for e in last_7 if e.goal_percentage is not None and e.goal_percentage >= 100]
    insights['goal_streak'] = len(goal_met)
    insights['goal_rate_7d'] = round(len(goal_met) / len(last_7) * 100) if last_7 else 0

    if last_30:
        goal_met_30 = [e for e in last_30 if e.goal_percentage is not None and e.goal_percentage >= 100]
        insights['goal_rate_30d'] = round(len(goal_met_30) / len(last_30) * 100)
    else:
        insights['goal_rate_30d'] = 0

    if last_7:
        avg_recent = sum(e.fluid_intake_ml for e in last_7) / len(last_7)
        if avg_recent < 1500:
            insights['alerts'].append({
                'level': 'warning',
                'message': f'Average intake of {avg_recent:.0f}ml/day is below recommended.',
            })

    insights['entries_last_7'] = len(last_7)
    insights['entries_last_30'] = len(last_30)
    return insights


def energy_insights(queryset):
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_7 = [e for e in entries if e.date >= today - timedelta(days=7)]
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {'has_data': True, 'alerts': [], 'tips': []}

    scores = [e.energy_score for e in entries]
    if scores:
        insights['energy_sparkline'] = _sparkline_points(scores[-14:])
        insights['energy_trend'] = _trend_direction(scores[-14:])
        insights['current_score'] = scores[-1]
        insights['avg_score_7d'] = round(sum(e.energy_score for e in last_7) / len(last_7), 1) if last_7 else None
        insights['avg_score_30d'] = round(sum(e.energy_score for e in last_30) / len(last_30), 1) if last_30 else None

    low_days = [e for e in last_7 if e.energy_score <= 3]
    if len(low_days) >= 3:
        insights['alerts'].append({
            'level': 'warning',
            'message': f'{len(low_days)} low-energy days in the last week.',
        })

    high_days = [e for e in last_7 if e.energy_score >= 8]
    if len(high_days) >= 5:
        insights['tips'].append('Excellent energy levels this week!')

    insights['entries_last_7'] = len(last_7)
    insights['entries_last_30'] = len(last_30)
    return insights


def pain_insights(queryset):
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {'has_data': True, 'alerts': [], 'tips': []}

    levels = [e.pain_level for e in entries]
    if levels:
        insights['pain_sparkline'] = _sparkline_points(levels[-14:])
        insights['pain_trend'] = _trend_direction(levels[-14:])
        insights['avg_pain_30d'] = round(sum(e.pain_level for e in last_30) / len(last_30), 1) if last_30 else None

    region_counts = {}
    for e in last_30:
        region_counts[e.body_region] = region_counts.get(e.body_region, 0) + 1
    if region_counts:
        insights['top_regions'] = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    severe = [e for e in last_30 if e.pain_level >= 7]
    if len(severe) >= 3:
        insights['alerts'].append({
            'level': 'error',
            'message': f'{len(severe)} severe pain episodes in the last 30 days.',
        })

    pain_dates = set(e.date for e in last_30)
    insights['pain_free_days'] = max(30 - len(pain_dates), 0)
    insights['entries_last_30'] = len(last_30)
    return insights


def metabolic_insights(queryset):
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {'has_data': True, 'alerts': [], 'tips': []}

    glucose_vals = [e.blood_glucose for e in entries if e.blood_glucose is not None]
    if glucose_vals:
        insights['glucose_sparkline'] = _sparkline_points(glucose_vals[-14:])
        insights['glucose_trend'] = _trend_direction(glucose_vals[-14:])
        insights['glucose_current'] = glucose_vals[-1]

        if glucose_vals[-1] > 126:
            insights['alerts'].append({
                'level': 'error',
                'message': f'Glucose of {glucose_vals[-1]} mg/dL is above normal range.',
            })
        elif glucose_vals[-1] > 100:
            insights['alerts'].append({
                'level': 'warning',
                'message': f'Glucose of {glucose_vals[-1]} mg/dL is in the pre-diabetic range.',
            })

    homa_entries = [e for e in entries if e.homa_ir is not None]
    if homa_entries:
        insights['homa_ir'] = homa_entries[-1].homa_ir
        insights['homa_category'] = homa_entries[-1].homa_ir_category

    insights['entries_last_30'] = len(last_30)
    return insights


def generic_tracking_insights(queryset, value_field=None):
    """Generic insights for any tracking model with a date field."""
    entries = list(queryset.order_by('date'))
    if not entries:
        return {'has_data': False}

    today = timezone.now().date()
    last_7 = [e for e in entries if e.date >= today - timedelta(days=7)]
    last_30 = [e for e in entries if e.date >= today - timedelta(days=30)]

    insights = {
        'has_data': True,
        'total_entries': len(entries),
        'entries_last_7': len(last_7),
        'entries_last_30': len(last_30),
        'alerts': [],
        'tips': [],
    }

    if value_field:
        values = [getattr(e, value_field) for e in entries if getattr(e, value_field, None) is not None]
        if values:
            insights['sparkline'] = _sparkline_points(values[-14:])
            insights['trend'] = _trend_direction(values[-14:])
            insights['current'] = values[-1]
            if len(values) >= 2:
                insights['change'] = round(values[-1] - values[-2], 2)
            recent_vals = [getattr(e, value_field) for e in last_30 if getattr(e, value_field, None) is not None]
            if recent_vals:
                insights['avg_30d'] = round(sum(recent_vals) / len(recent_vals), 1)

    return insights
