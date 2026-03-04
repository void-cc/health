"""
RxNorm/RxNav API helper for medication autocomplete and drug interaction checking.

Privacy: only drug names / RxCUIs are sent to the external API — no user data.
All results are cached locally in MedicationConcept and PharmacologicalInteraction.
"""
import logging
import time
import urllib.parse
import requests

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
TIMEOUT = 5  # seconds

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Negative cache: RxCUIs that returned 404 (avoid repeat lookups for TTL secs)
# ---------------------------------------------------------------------------

_NOT_FOUND_TTL = 3600  # 1 hour
_not_found_cache = {}  # {rxcui: expiry_timestamp}


def _mark_not_found(rxcui):
    """Record that this RxCUI returned 404; suppress repeated lookups for TTL."""
    _not_found_cache[rxcui] = time.time() + _NOT_FOUND_TTL


def _is_not_found(rxcui):
    """Return True if rxcui is in the negative cache and the TTL has not expired."""
    expiry = _not_found_cache.get(rxcui)
    if expiry is None:
        return False
    if time.time() > expiry:
        del _not_found_cache[rxcui]
        return False
    return True


def _get(url, params=None):
    """
    Execute a GET request; return parsed JSON or None on failure.

    - HTTP 404 → DEBUG log, return None (expected "not found").
    - HTTP 429 → WARNING log, return None (rate-limited).
    - Other HTTP/network errors → WARNING log, return None.
    """
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code == 404:
            logger.debug("Drug API resource not found (404): %s", url)
            return None
        if resp.status_code == 429:
            logger.warning("Drug API rate-limited (429): %s", url)
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as exc:
        logger.warning("Drug API HTTP error: %s", exc)
        return None
    except requests.exceptions.Timeout:
        logger.warning("Drug API request timed out: %s", url)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Drug API connection error: %s", url)
        return None
    except Exception as exc:
        logger.warning("Drug API request failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Fallback drug-name providers
# ---------------------------------------------------------------------------

def _search_openfda(query, max_results=10):
    """Search openFDA Drug Label API for brand/generic names."""
    try:
        from django.conf import settings
        if not getattr(settings, 'DRUG_PROVIDER_OPENFDA_ENABLED', True):
            return []
    except Exception:
        pass
    data = _get(
        "https://api.fda.gov/drug/label.json",
        params={'search': f'openfda.brand_name:"{query}"', 'limit': max_results},
    )
    results = []
    if data:
        for hit in (data.get('results') or []):
            openfda = hit.get('openfda', {})
            names = openfda.get('brand_name') or openfda.get('generic_name') or []
            for name in names[:1]:
                results.append({'name': name, 'rxcui': '', 'source': 'openfda'})
    return results[:max_results]


def _search_dailymed(query, max_results=10):
    """Search DailyMed (NIH/NLM) for drug names."""
    try:
        from django.conf import settings
        if not getattr(settings, 'DRUG_PROVIDER_DAILYMED_ENABLED', True):
            return []
    except Exception:
        pass
    data = _get(
        "https://dailymed.nlm.nih.gov/dailymed/services/v2/drugnames.json",
        params={'drug_name': query, 'pagesize': max_results},
    )
    results = []
    if data:
        for item in (data.get('data') or []):
            name = item.get('drug_name') or item.get('drugname')
            if name:
                results.append({'name': name, 'rxcui': '', 'source': 'dailymed'})
    return results[:max_results]


def _search_wikidata(query, max_results=10):
    """Search Wikidata for medication entity labels via the MediaWiki API."""
    try:
        from django.conf import settings
        if not getattr(settings, 'DRUG_PROVIDER_WIKIDATA_ENABLED', True):
            return []
    except Exception:
        pass
    data = _get(
        "https://www.wikidata.org/w/api.php",
        params={
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'type': 'item',
            'limit': max_results,
            'format': 'json',
        },
    )
    results = []
    if data:
        for item in (data.get('search') or []):
            label = item.get('label') or (
                item.get('display', {}).get('label', {}).get('value')
            )
            if label:
                results.append({'name': label, 'rxcui': '', 'source': 'wikidata'})
    return results[:max_results]


def _search_pubchem(query, max_results=10):
    """Search PubChem for compound synonyms."""
    try:
        from django.conf import settings
        if not getattr(settings, 'DRUG_PROVIDER_PUBCHEM_ENABLED', True):
            return []
    except Exception:
        pass
    encoded = urllib.parse.quote(query, safe='')
    data = _get(
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/synonyms/JSON",
    )
    results = []
    if data:
        for entry in (data.get('InformationList', {}).get('Information') or []):
            for syn in (entry.get('Synonym') or [])[:max_results]:
                results.append({'name': syn, 'rxcui': '', 'source': 'pubchem'})
    return results[:max_results]


# ---------------------------------------------------------------------------
# Autocomplete / name search
# ---------------------------------------------------------------------------

def search_medication_names(query, max_results=10):
    """
    Return a list of dicts with 'name', 'rxcui', and 'source' for medications
    matching *query*.

    Order of lookup:
        1. Local cache (MedicationConcept)
        2. RxNorm / RxNav API
        3. openFDA → DailyMed → Wikidata → PubChem (until max_results is met)

    Results are deduplicated by name.  Successful external lookups are cached
    locally so subsequent searches avoid external API calls.

    Returns list of {'name': str, 'rxcui': str, 'source': str} dicts.
    """
    from .models import MedicationConcept

    query = query.strip()
    if not query:
        return []

    # 1. Local cache lookup (fast path)
    local_qs = MedicationConcept.objects.filter(
        name__icontains=query
    ).values('name', 'rxcui', 'source')[:max_results]
    local = [{'name': r['name'], 'rxcui': r['rxcui'], 'source': r['source']} for r in local_qs]
    if local:
        return local

    seen_names = set()
    results = []

    # 2. RxNorm approximate-term lookup
    data = _get(
        f"{RXNAV_BASE}/approximateTerm.json",
        params={'term': query, 'maxEntries': max_results},
    )
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
                if name not in seen_names:
                    seen_names.add(name)
                    results.append({'name': name, 'rxcui': rxcui, 'source': 'rxnorm'})
                    # Cache locally
                    MedicationConcept.objects.get_or_create(
                        rxcui=rxcui,
                        defaults={'name': name, 'source': 'rxnorm'},
                    )

    # 3. Fallback providers (when RxNorm returned nothing or not enough results)
    if len(results) < max_results:
        for provider in (_search_openfda, _search_dailymed, _search_wikidata, _search_pubchem):
            if len(results) >= max_results:
                break
            for item in provider(query, max_results - len(results)):
                if item['name'] not in seen_names:
                    seen_names.add(item['name'])
                    results.append(item)
                    # Cache successful fallback results locally
                    MedicationConcept.objects.get_or_create(
                        name=item['name'],
                        defaults={
                            'rxcui': item.get('rxcui', ''),
                            'source': item['source'],
                        },
                    )

    return results[:max_results]


# ---------------------------------------------------------------------------
# RxNorm name lookup
# ---------------------------------------------------------------------------

def _get_rxnorm_name(rxcui):
    """Retrieve the preferred display name for an RxCUI."""
    if _is_not_found(rxcui):
        return None
    data = _get(
        f"{RXNAV_BASE}/rxcui/{rxcui}/property.json",
        params={'propName': 'RxNorm Name'},
    )
    if data:
        props = data.get('propConceptGroup', {}).get('propConcept') or []
        for prop in props:
            if prop.get('propValue'):
                return prop['propValue']
    # property.json returned nothing useful; record as not found to avoid
    # repeated requests (the allinfo.json endpoint is a common 404 source).
    _mark_not_found(rxcui)
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
        if concept:
            concept.__class__.objects.filter(pk=concept.pk).update(rxcui=rxcui)
        else:
            MedicationConcept.objects.update_or_create(
                name=drug_name,
                defaults={'rxcui': rxcui, 'source': 'rxnorm'},
            )
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
            medication_a=idata['medication_a'],
            medication_b=idata['medication_b'],
            defaults={
                'severity': idata['severity'],
                'description': idata['description'],
                'source': idata['source'],
                'reference_url': idata.get('reference_url', ''),
            },
        )
        saved.append(obj)
    return saved
