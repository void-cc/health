from django.urls import reverse, NoReverseMatch


# Centralized sidebar navigation configuration.
# Each category has a title and a list of items. Each item specifies:
#   - label: display text
#   - icon: Lucide icon name (rendered via the Lucide sprite/JS in base template)
#   - url_name: the Django URL name used to generate the link
#   - match: list of substrings; if any appears in the current URL name,
#            the item is marked active
# Categories marked with "collapsible": True are rendered as toggleable
# groups in the sidebar so that secondary links don't clutter the view.
SIDEBAR_CONFIG = [
    {
        "category": "Overview",
        "items": [
            {"label": "Dashboard", "icon": "layout-dashboard", "url_name": "index", "match": ["index"]},
            {"label": "Timeline", "icon": "clock", "url_name": "timeline", "match": ["timeline"]},
            {"label": "Labs", "icon": "flask-conical", "url_name": "labs_dashboard", "match": ["labs_dashboard"]},
            {"label": "Vitals", "icon": "heart-pulse", "url_name": "vitals", "match": ["vitals", "add_vitals", "edit_vitals"]},
        ],
    },
    {
        "category": "Analytics",
        "items": [
            {"label": "Blood Charts", "icon": "trending-up", "url_name": "blood_tests_charts", "match": ["blood_tests_charts"]},
            {"label": "Boxplots", "icon": "bar-chart-3", "url_name": "blood_tests_boxplots", "match": ["blood_tests_boxplots"]},
            {"label": "Compare", "icon": "git-compare-arrows", "url_name": "comparative_bar_charts", "match": ["comparative_bar_charts"]},
            {"label": "Vitals Charts", "icon": "activity", "url_name": "vitals_charts", "match": ["vitals_charts"]},
            {"label": "Scatter Plots", "icon": "scatter-chart", "url_name": "scatter_plots", "match": ["scatter_plots"]},
        ],
    },
    {
        "category": "Tracking",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Body Composition", "icon": "scale", "url_name": "body_composition_list", "match": ["body_composition"]},
            {"label": "Hydration", "icon": "droplets", "url_name": "hydration_list", "match": ["hydration"]},
            {"label": "Energy", "icon": "zap", "url_name": "energy_list", "match": ["energy"]},
            {"label": "Metabolic Rate", "icon": "flame", "url_name": "rmr_list", "match": ["rmr"]},
            {"label": "Pain", "icon": "cross", "url_name": "pain_list", "match": ["pain"]},
            {"label": "Symptoms", "icon": "clipboard-list", "url_name": "symptom_list", "match": ["symptom"]},
            {"label": "Reproductive", "icon": "heart", "url_name": "reproductive_list", "match": ["reproductive"]},
            {"label": "Orthostatic", "icon": "arrow-up-down", "url_name": "orthostatic_list", "match": ["orthostatic"]},
            {"label": "Glucose", "icon": "test-tube", "url_name": "metabolic_list", "match": ["metabolic"]},
            {"label": "Ketones", "icon": "beaker", "url_name": "ketone_list", "match": ["ketone"]},
            {"label": "Custom Vitals", "icon": "sliders-horizontal", "url_name": "custom_vitals_list", "match": ["custom_vitals"]},
        ],
    },
    {
        "category": "Sleep & Nutrition",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Sleep Analytics", "icon": "bar-chart-2", "url_name": "sleep_dashboard", "match": ["sleep_dashboard"]},
            {"label": "Sleep Tracking", "icon": "moon", "url_name": "sleep_list", "match": ["sleep"]},
            {"label": "Circadian", "icon": "sun-moon", "url_name": "circadian_list", "match": ["circadian"]},
            {"label": "Dream Journal", "icon": "cloud-moon", "url_name": "dream_list", "match": ["dream"]},
            {"label": "Nutrition Analytics", "icon": "pie-chart", "url_name": "nutrition_dashboard", "match": ["nutrition_dashboard"]},
            {"label": "Macronutrients", "icon": "utensils", "url_name": "macro_list", "match": ["macro"]},
            {"label": "Micronutrients", "icon": "pill", "url_name": "micro_list", "match": ["micro"]},
            {"label": "Food Entries", "icon": "apple", "url_name": "food_list", "match": ["food"]},
            {"label": "Fasting", "icon": "timer", "url_name": "fasting_list", "match": ["fasting"]},
            {"label": "Caffeine & Alcohol", "icon": "coffee", "url_name": "caffeine_alcohol_list", "match": ["caffeine_alcohol"]},
        ],
    },
    {
        "category": "Medications",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Schedules", "icon": "calendar-clock", "url_name": "medication_schedule_list", "match": ["medication_schedule"]},
            {"label": "Dose Log", "icon": "clipboard-check", "url_name": "medication_log_list", "match": ["medication_log"]},
            {"label": "Inventory", "icon": "package", "url_name": "medication_inventory_list", "match": ["medication_inventory"]},
            {"label": "Interactions", "icon": "alert-circle", "url_name": "pharmacological_interaction_list", "match": ["pharmacological_interaction"]},
        ],
    },
    {
        "category": "Intelligence",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Health Goals", "icon": "target", "url_name": "health_goal_list", "match": ["health_goal"]},
            {"label": "Critical Alerts", "icon": "alert-triangle", "url_name": "critical_alert_list", "match": ["critical_alert"]},
            {"label": "Health Reports", "icon": "file-text", "url_name": "health_report_list", "match": ["health_report"]},
            {"label": "Biological Age", "icon": "dna", "url_name": "biological_age_list", "match": ["biological_age"]},
            {"label": "Predictive Biomarkers", "icon": "microscope", "url_name": "predictive_biomarker_list", "match": ["predictive_biomarker"]},
        ],
    },
    {
        "category": "Devices",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Wearable Devices", "icon": "watch", "url_name": "wearable_device_list", "match": ["wearable_device"]},
            {"label": "Sync Logs", "icon": "refresh-cw", "url_name": "sync_log_list", "match": ["sync_log"]},
            {"label": "Integration Config", "icon": "plug", "url_name": "integration_config_list", "match": ["integration_config"]},
            {"label": "Integration Sub-tasks", "icon": "list-checks", "url_name": "integration_subtask_list", "match": ["integration_subtask"]},
        ],
    },
    {
        "category": "Sharing",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "Secure Links", "icon": "link", "url_name": "secure_viewing_link_list", "match": ["secure_viewing_link"]},
            {"label": "Practitioner Access", "icon": "stethoscope", "url_name": "practitioner_access_list", "match": ["practitioner_access", "practitioner_portal"]},
            {"label": "Intake Summaries", "icon": "clipboard", "url_name": "intake_summary_list", "match": ["intake_summary"]},
            {"label": "Data Exports", "icon": "download", "url_name": "data_export_list", "match": ["data_export"]},
            {"label": "Stakeholder Emails", "icon": "mail", "url_name": "stakeholder_email_list", "match": ["stakeholder_email"]},
        ],
    },
    {
        "category": "Settings",
        "collapsible": True,
        "items": [
            {"label": "Profile", "icon": "user", "url_name": "profile", "match": ["profile"]},
            {"label": "Privacy", "icon": "lock", "url_name": "privacy_preferences", "match": ["privacy_preferences"]},
            {"label": "Security Log", "icon": "shield", "url_name": "security_log", "match": ["security_log"]},
            {"label": "Sessions", "icon": "monitor", "url_name": "active_sessions", "match": ["active_sessions"]},
            {"label": "Import Data", "icon": "upload", "url_name": "import_data", "match": ["import_data"]},
            {"label": "Export Data", "icon": "download", "url_name": "export_data", "match": ["export_data"]},
            {"label": "Customize Dashboard", "icon": "settings", "url_name": "customize_dashboard", "match": ["customize_dashboard"]},
            {"label": "Logout", "icon": "log-out", "url_name": "logout", "match": []},
        ],
    },
    {
        "category": "Administration",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "History", "icon": "history", "url_name": "history", "match": ["history"]},
            {"label": "Add Test", "icon": "plus-circle", "url_name": "add_test", "match": ["add_test"]},
            {"label": "Add Test Info", "icon": "info", "url_name": "add_test_info", "match": ["add_test_info"]},
            {"label": "Bulk Edit", "icon": "table-2", "url_name": "bulk_edit", "match": ["bulk_edit"]},
            {"label": "User Profiles", "icon": "users", "url_name": "user_profile_list", "match": ["user_profile"]},
            {"label": "Family Accounts", "icon": "home", "url_name": "family_account_list", "match": ["family_account"]},
            {"label": "Consent Logs", "icon": "handshake", "url_name": "consent_log_list", "match": ["consent_log"]},
            {"label": "Audit Logs", "icon": "scroll-text", "url_name": "audit_log_list", "match": ["audit_log"]},
        ],
    },
]


def sidebar_nav(request):
    """Context processor that builds the sidebar navigation dynamically.

    Each category is included only when at least one of its items can be
    resolved to a URL (i.e. the route actually exists in urlconf).  This
    means newly-added URL patterns automatically appear in the sidebar
    once they are registered in ``SIDEBAR_CONFIG``, and removed patterns
    silently disappear.

    Categories with ``"collapsible": True`` are rendered as toggleable
    groups in the sidebar template.  They are auto-expanded when one of
    their items is active.

    Categories with ``"staff_only": True`` are hidden from non-staff users.
    """
    current_url_name = ""
    if hasattr(request, "resolver_match") and request.resolver_match:
        current_url_name = request.resolver_match.url_name or ""

    is_staff = hasattr(request, "user") and request.user.is_authenticated and request.user.is_staff

    nav = []
    for section in SIDEBAR_CONFIG:
        if section.get("staff_only") and not is_staff:
            continue
        resolved_items = []
        section_has_active = False
        for item in section["items"]:
            try:
                url = reverse(item["url_name"])
            except NoReverseMatch:
                continue
            active = any(m in current_url_name for m in item["match"])
            if active:
                section_has_active = True
            resolved_items.append(
                {
                    "label": item["label"],
                    "icon": item["icon"],
                    "url": url,
                    "active": active,
                }
            )
        if resolved_items:
            nav.append(
                {
                    "category": section["category"],
                    "items": resolved_items,
                    "collapsible": section.get("collapsible", False),
                    "expanded": section_has_active,
                }
            )
    return {"sidebar_nav": nav}
