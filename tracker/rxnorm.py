"""
RxNorm/RxNav API helper for medication autocomplete and drug interaction checking.

Privacy: only drug names / RxCUIs are sent to the external API — no user data.
All results are cached locally in MedicationConcept and PharmacologicalInteraction.
"""
import logging
import requests

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
TIMEOUT = 5  # seconds

logger = logging.getLogger(__name__)


def _get(url, params=None):
    """Execute a GET request to RxNav; return parsed JSON or None on failure."""
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("RxNorm API request failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Autocomplete / name search
# ---------------------------------------------------------------------------

def search_medication_names(query, max_results=10):
    """
    Return a list of dicts with 'name' and 'rxcui' for medications matching
    *query*.  Searches local cache first; falls back to the RxNorm API.

    Returns list of {'name': str, 'rxcui': str} dicts.
    """
    from .models import MedicationConcept

    query = query.strip()
    if not query:
        return []

    # 1. Local cache lookup (fast path)
    local_qs = MedicationConcept.objects.filter(
        name__icontains=query
    ).values('name', 'rxcui')[:max_results]
    local = [{'name': r['name'], 'rxcui': r['rxcui']} for r in local_qs]
    if local:
        return local

    # 2. RxNorm approximate-term lookup
    data = _get(
        f"{RXNAV_BASE}/approximateTerm.json",
        params={'term': query, 'maxEntries': max_results},
    )
    results = []
    if data:
        candidates = (
            data.get('approximateGroup', {}).get('candidate') or []
        )
        seen_rxcui = set()
        for cand in candidates:
            rxcui = cand.get('rxcui', '')
            if rxcui and rxcui not in seen_rxcui:
                seen_rxcui.add(rxcui)
                name = _get_rxnorm_name(rxcui) or rxcui
                results.append({'name': name, 'rxcui': rxcui})
                # Cache locally
                MedicationConcept.objects.get_or_create(
                    rxcui=rxcui,
                    defaults={'name': name, 'source': 'rxnorm'},
                )

    return results[:max_results]


def _get_rxnorm_name(rxcui):
    """Retrieve the preferred display name for an RxCUI."""
    data = _get(
        f"{RXNAV_BASE}/rxcui/{rxcui}/property.json",
        params={'propName': 'RxNorm Name'},
    )
    if data:
        props = data.get('propConceptGroup', {}).get('propConcept') or []
        for prop in props:
            if prop.get('propValue'):
                return prop['propValue']
    # Fallback: use the drugs endpoint
    data2 = _get(f"{RXNAV_BASE}/rxcui/{rxcui}/allinfo.json")
    if data2:
        info = data2.get('rxcuiStatusInfo', {})
        return info.get('str') or None
    return None


def get_rxcui(drug_name):
    """
    Look up the RxCUI for a drug name.  Returns the RxCUI string or '' on
    failure.  Results are cached in MedicationConcept.
    """
    from .models import MedicationConcept

    drug_name = drug_name.strip()
    if not drug_name:
        return ''

    # Local cache
    concept = MedicationConcept.objects.filter(
        name__iexact=drug_name
    ).first()
    if concept and concept.rxcui:
        return concept.rxcui

    data = _get(
        f"{RXNAV_BASE}/rxcui.json",
        params={'name': drug_name, 'search': 2},
    )
    if not data:
        return ''
    rxcui = data.get('idGroup', {}).get('rxnormId') or []
    rxcui = rxcui[0] if rxcui else ''
    if rxcui:
        MedicationConcept.objects.update_or_create(
            name__iexact=drug_name,
            defaults={'name': drug_name, 'rxcui': rxcui, 'source': 'rxnorm'},
        ) if not concept else concept.__class__.objects.filter(
            pk=concept.pk
        ).update(rxcui=rxcui)
    return rxcui


# ---------------------------------------------------------------------------
# Interaction checking
# ---------------------------------------------------------------------------

def check_interactions(drug_names):
    """
    Check drug-drug (and food/supplement) interactions for a list of drug
    names using the RxNorm interaction API.

    Returns a list of dicts::

        {
            'medication_a': str,
            'medication_b': str,
            'severity': 'low' | 'moderate' | 'high' | 'critical',
            'description': str,
            'source': 'rxnorm',
            'reference_url': str,
        }

    If the API is unavailable an empty list is returned (graceful degradation).
    """
    if len(drug_names) < 2:
        return []

    # Resolve RxCUIs (only drugs with a known RXCUI can be checked)
    rxcui_map = {}  # rxcui -> original name
    for name in drug_names:
        rxcui = get_rxcui(name)
        if rxcui:
            rxcui_map[rxcui] = name

    if len(rxcui_map) < 2:
        return []

    rxcui_list = '+'.join(rxcui_map.keys())
    data = _get(
        f"{RXNAV_BASE}/interaction/list.json",
        params={'rxcuis': rxcui_list},
    )
    if not data:
        return []

    interactions = []
    full_groups = data.get('fullInteractionTypeGroup') or []
    for group in full_groups:
        for itype in (group.get('fullInteractionType') or []):
            for pair in (itype.get('interactionPair') or []):
                concepts = pair.get('interactionConcept') or []
                if len(concepts) < 2:
                    continue
                name_a = (
                    concepts[0].get('minConceptItem', {}).get('name') or
                    rxcui_map.get(
                        concepts[0].get('minConceptItem', {}).get('rxcui', ''), ''
                    )
                )
                name_b = (
                    concepts[1].get('minConceptItem', {}).get('name') or
                    rxcui_map.get(
                        concepts[1].get('minConceptItem', {}).get('rxcui', ''), ''
                    )
                )
                severity_text = (pair.get('severity') or 'low').lower()
                severity = _map_severity(severity_text)
                description = pair.get('description') or ''
                interactions.append({
                    'medication_a': name_a,
                    'medication_b': name_b,
                    'severity': severity,
                    'description': description,
                    'source': 'rxnorm',
                    'reference_url': '',
                })

    return interactions


def _map_severity(rxnorm_severity):
    """Map RxNorm severity strings to our internal severity choices."""
    mapping = {
        'high': 'high',
        'critical': 'critical',
        'moderate': 'moderate',
        'medium': 'moderate',
        'low': 'low',
        'minor': 'low',
    }
    return mapping.get(rxnorm_severity, 'low')


def run_interaction_check_for_user(user, new_medication_name):
    """
    Run an interaction check for *new_medication_name* against all of
    *user*'s currently active medication schedules.

    Persists any new interactions to PharmacologicalInteraction (tagged with
    the user so they appear on the interaction dashboard).

    Returns a list of PharmacologicalInteraction instances created/found.
    """
    from .models import MedicationSchedule, PharmacologicalInteraction

    active_names = list(
        MedicationSchedule.objects.filter(
            user=user, is_active=True
        ).exclude(
            medication_name__iexact=new_medication_name
        ).values_list('medication_name', flat=True)
    )

    all_names = [new_medication_name] + active_names
    if len(all_names) < 2:
        return []

    raw = check_interactions(all_names)
    saved = []
    for idata in raw:
        obj, _ = PharmacologicalInteraction.objects.get_or_create(
            user=user,
            medication_a__iexact=idata['medication_a'],
            medication_b__iexact=idata['medication_b'],
            defaults={
                'medication_a': idata['medication_a'],
                'medication_b': idata['medication_b'],
                'severity': idata['severity'],
                'description': idata['description'],
                'source': idata['source'],
                'reference_url': idata.get('reference_url', ''),
            },
        )
        saved.append(obj)
    return saved
