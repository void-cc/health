from django.urls import reverse, NoReverseMatch


# Centralized sidebar navigation configuration.
# Each category has a title and a list of items. Each item specifies:
#   - label: display text
#   - icon: Font Awesome icon class
#   - url_name: the Django URL name used to generate the link
#   - match: list of substrings; if any appears in the current URL name,
#            the item is marked active
# Categories marked with "collapsible": True are rendered as toggleable
# groups in the sidebar so that secondary links don't clutter the view.
SIDEBAR_CONFIG = [
    {
        "category": "Overview",
        "items": [
            {"label": "Dashboard", "icon": "fa-th-large", "url_name": "index", "match": ["index"]},
            {"label": "Timeline", "icon": "fa-stream", "url_name": "timeline", "match": ["timeline"]},
            {"label": "Labs", "icon": "fa-flask", "url_name": "labs_dashboard", "match": ["labs_dashboard"]},
            {"label": "Vitals", "icon": "fa-heartbeat", "url_name": "vitals", "match": ["vitals", "add_vitals", "edit_vitals"]},
        ],
    },
    {
        "category": "Analytics",
        "items": [
            {"label": "Blood Charts", "icon": "fa-chart-line", "url_name": "blood_tests_charts", "match": ["blood_tests_charts"]},
            {"label": "Boxplots", "icon": "fa-chart-bar", "url_name": "blood_tests_boxplots", "match": ["blood_tests_boxplots"]},
            {"label": "Compare to Normal", "icon": "fa-chart-bar", "url_name": "comparative_bar_charts", "match": ["comparative_bar_charts"]},
            {"label": "Vitals Charts", "icon": "fa-chart-area", "url_name": "vitals_charts", "match": ["vitals_charts"]},
            {"label": "Scatter Plots", "icon": "fa-project-diagram", "url_name": "scatter_plots", "match": ["scatter_plots"]},
        ],
    },
    {
        "category": "Tracking",
        "collapsible": True,
        "items": [
            {"label": "Body Composition", "icon": "fa-weight", "url_name": "body_composition_list", "match": ["body_composition"]},
            {"label": "Hydration", "icon": "fa-tint", "url_name": "hydration_list", "match": ["hydration"]},
            {"label": "Energy & Fatigue", "icon": "fa-battery-half", "url_name": "energy_list", "match": ["energy"]},
            {"label": "Metabolic Rate", "icon": "fa-fire", "url_name": "rmr_list", "match": ["rmr"]},
            {"label": "Pain Mapping", "icon": "fa-user-injured", "url_name": "pain_list", "match": ["pain"]},
            {"label": "Symptom Journal", "icon": "fa-notes-medical", "url_name": "symptom_list", "match": ["symptom"]},
            {"label": "Reproductive Health", "icon": "fa-venus", "url_name": "reproductive_list", "match": ["reproductive"]},
            {"label": "Orthostatic", "icon": "fa-heartbeat", "url_name": "orthostatic_list", "match": ["orthostatic"]},
            {"label": "Glucose & Insulin", "icon": "fa-vial", "url_name": "metabolic_list", "match": ["metabolic"]},
            {"label": "Ketones", "icon": "fa-flask", "url_name": "ketone_list", "match": ["ketone"]},
            {"label": "Custom Vitals", "icon": "fa-sliders-h", "url_name": "custom_vitals_list", "match": ["custom_vitals"]},
        ],
    },
    {
        "category": "Sleep & Nutrition",
        "collapsible": True,
        "items": [
            {"label": "Sleep Tracking", "icon": "fa-bed", "url_name": "sleep_list", "match": ["sleep"]},
            {"label": "Circadian Rhythm", "icon": "fa-clock", "url_name": "circadian_list", "match": ["circadian"]},
            {"label": "Dream Journal", "icon": "fa-cloud-moon", "url_name": "dream_list", "match": ["dream"]},
            {"label": "Macronutrients", "icon": "fa-drumstick-bite", "url_name": "macro_list", "match": ["macro"]},
            {"label": "Micronutrients", "icon": "fa-capsules", "url_name": "micro_list", "match": ["micro"]},
            {"label": "Food Entries", "icon": "fa-utensils", "url_name": "food_list", "match": ["food"]},
            {"label": "Fasting", "icon": "fa-hourglass-half", "url_name": "fasting_list", "match": ["fasting"]},
            {"label": "Caffeine & Alcohol", "icon": "fa-coffee", "url_name": "caffeine_alcohol_list", "match": ["caffeine_alcohol"]},
        ],
    },
    {
        "category": "Medications",
        "collapsible": True,
        "items": [
            {"label": "Schedules", "icon": "fa-pills", "url_name": "medication_schedule_list", "match": ["medication_schedule"]},
            {"label": "Dose Log", "icon": "fa-clipboard-check", "url_name": "medication_log_list", "match": ["medication_log"]},
            {"label": "Inventory", "icon": "fa-boxes", "url_name": "medication_inventory_list", "match": ["medication_inventory"]},
            {"label": "Interactions", "icon": "fa-exclamation-circle", "url_name": "pharmacological_interaction_list", "match": ["pharmacological_interaction"]},
        ],
    },
    {
        "category": "Intelligence",
        "collapsible": True,
        "items": [
            {"label": "Health Goals", "icon": "fa-bullseye", "url_name": "health_goal_list", "match": ["health_goal"]},
            {"label": "Critical Alerts", "icon": "fa-exclamation-triangle", "url_name": "critical_alert_list", "match": ["critical_alert"]},
            {"label": "Health Reports", "icon": "fa-file-medical-alt", "url_name": "health_report_list", "match": ["health_report"]},
            {"label": "Biological Age", "icon": "fa-dna", "url_name": "biological_age_list", "match": ["biological_age"]},
            {"label": "Predictive Biomarkers", "icon": "fa-microscope", "url_name": "predictive_biomarker_list", "match": ["predictive_biomarker"]},
            {"label": "Clinical Trials", "icon": "fa-flask", "url_name": "clinical_trial_list", "match": ["clinical_trial"]},
        ],
    },
    {
        "category": "Devices",
        "collapsible": True,
        "items": [
            {"label": "Wearable Devices", "icon": "fa-mobile-alt", "url_name": "wearable_device_list", "match": ["wearable_device"]},
            {"label": "Sync Logs", "icon": "fa-sync-alt", "url_name": "sync_log_list", "match": ["sync_log"]},
            {"label": "Integration Config", "icon": "fa-plug", "url_name": "integration_config_list", "match": ["integration_config"]},
            {"label": "Integration Sub-tasks", "icon": "fa-tasks", "url_name": "integration_subtask_list", "match": ["integration_subtask"]},
        ],
    },
    {
        "category": "Sharing",
        "collapsible": True,
        "items": [
            {"label": "Secure Links", "icon": "fa-link", "url_name": "secure_viewing_link_list", "match": ["secure_viewing_link"]},
            {"label": "Practitioner Access", "icon": "fa-user-md", "url_name": "practitioner_access_list", "match": ["practitioner_access", "practitioner_portal"]},
            {"label": "Intake Summaries", "icon": "fa-clipboard-list", "url_name": "intake_summary_list", "match": ["intake_summary"]},
            {"label": "Data Exports", "icon": "fa-file-export", "url_name": "data_export_list", "match": ["data_export"]},
            {"label": "Stakeholder Emails", "icon": "fa-envelope", "url_name": "stakeholder_email_list", "match": ["stakeholder_email"]},
        ],
    },
    {
        "category": "Settings",
        "collapsible": True,
        "items": [
            {"label": "Profile", "icon": "fa-user", "url_name": "profile", "match": ["profile"]},
            {"label": "Privacy", "icon": "fa-lock", "url_name": "privacy_preferences", "match": ["privacy_preferences"]},
            {"label": "Security Log", "icon": "fa-shield-alt", "url_name": "security_log", "match": ["security_log"]},
            {"label": "Sessions", "icon": "fa-desktop", "url_name": "active_sessions", "match": ["active_sessions"]},
            {"label": "Import Data", "icon": "fa-file-upload", "url_name": "import_data", "match": ["import_data"]},
            {"label": "Export Data", "icon": "fa-file-download", "url_name": "export_data", "match": ["export_data"]},
            {"label": "Customize Dashboard", "icon": "fa-cog", "url_name": "customize_dashboard", "match": ["customize_dashboard"]},
            {"label": "Add Test Info", "icon": "fa-info-circle", "url_name": "add_test_info", "match": ["add_test_info"]},
            {"label": "Bulk Edit", "icon": "fa-table", "url_name": "bulk_edit", "match": ["bulk_edit"]},
            {"label": "Logout", "icon": "fa-sign-out-alt", "url_name": "logout", "match": []},
        ],
    },
    {
        "category": "Administration",
        "collapsible": True,
        "staff_only": True,
        "items": [
            {"label": "History", "icon": "fa-clock", "url_name": "history", "match": ["history"]},
            {"label": "Add Test", "icon": "fa-plus-circle", "url_name": "add_test", "match": ["add_test"]},
            {"label": "User Profiles", "icon": "fa-users", "url_name": "user_profile_list", "match": ["user_profile"]},
            {"label": "Family Accounts", "icon": "fa-home", "url_name": "family_account_list", "match": ["family_account"]},
            {"label": "Consent Logs", "icon": "fa-handshake", "url_name": "consent_log_list", "match": ["consent_log"]},
            {"label": "Tenant Config", "icon": "fa-building", "url_name": "tenant_config_list", "match": ["tenant_config"]},
            {"label": "Admin Telemetry", "icon": "fa-chart-pie", "url_name": "admin_telemetry_list", "match": ["admin_telemetry"]},
            {"label": "API Rate Limits", "icon": "fa-tachometer-alt", "url_name": "api_rate_limit_list", "match": ["api_rate_limit"]},
            {"label": "Encryption Keys", "icon": "fa-key", "url_name": "encryption_key_list", "match": ["encryption_key"]},
            {"label": "Audit Logs", "icon": "fa-scroll", "url_name": "audit_log_list", "match": ["audit_log"]},
            {"label": "Anonymized Data", "icon": "fa-user-secret", "url_name": "anonymized_data_list", "match": ["anonymized_data"]},
            {"label": "Database Scaling", "icon": "fa-database", "url_name": "database_scaling_list", "match": ["database_scaling"]},
            {"label": "Backup Config", "icon": "fa-hdd", "url_name": "backup_config_list", "match": ["backup_config"]},
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
