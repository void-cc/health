from django.contrib import admin
from .models import (
    SleepLog, CircadianRhythmLog, DreamJournal, MacronutrientLog,
    MicronutrientLog, FoodEntry, FastingLog, CaffeineAlcoholLog,
    ClinicalTrialMatch, HabitLog, Reminder,
    NotificationPreference, NotificationTemplate, NotificationTrigger,
    NotificationLog,
    MedicationLog, MedicationInventory,
)


@admin.register(SleepLog)
class SleepLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'bedtime', 'wake_time', 'total_sleep_minutes', 'sleep_quality_score')
    list_filter = ('date',)
    search_fields = ('notes',)


@admin.register(CircadianRhythmLog)
class CircadianRhythmLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'wake_time', 'sleep_onset', 'peak_energy_time', 'light_exposure_minutes')
    list_filter = ('date',)


@admin.register(DreamJournal)
class DreamJournalAdmin(admin.ModelAdmin):
    list_display = ('date', 'lucidity_level', 'mood_on_waking')
    list_filter = ('date', 'lucidity_level')
    search_fields = ('dream_description', 'notes')


@admin.register(MacronutrientLog)
class MacronutrientLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'protein_grams', 'carbohydrate_grams', 'fat_grams', 'calories')
    list_filter = ('date',)


@admin.register(MicronutrientLog)
class MicronutrientLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'nutrient_name', 'amount', 'unit', 'deficiency_risk')
    list_filter = ('date', 'nutrient_name', 'deficiency_risk')
    search_fields = ('nutrient_name', 'notes')


@admin.register(FoodEntry)
class FoodEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'food_name', 'calories', 'source', 'barcode')
    list_filter = ('date', 'source')
    search_fields = ('food_name', 'barcode', 'food_database_id')


@admin.register(FastingLog)
class FastingLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'fast_start', 'fast_end', 'target_hours', 'actual_hours')
    list_filter = ('date',)


@admin.register(CaffeineAlcoholLog)
class CaffeineAlcoholLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'substance', 'drink_name', 'amount_mg', 'time_consumed')
    list_filter = ('date', 'substance')
    search_fields = ('drink_name', 'notes')


@admin.register(ClinicalTrialMatch)
class ClinicalTrialMatchAdmin(admin.ModelAdmin):
    list_display = ('trial_id', 'trial_title', 'condition', 'match_score', 'status', 'found_at')
    list_filter = ('status', 'condition')
    search_fields = ('trial_id', 'trial_title', 'condition')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'sms_enabled', 'push_enabled', 'updated_at')
    list_filter = ('email_enabled', 'sms_enabled', 'push_enabled')
    search_fields = ('user__username', 'user__email')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'channel', 'subject', 'is_active', 'updated_at')
    list_filter = ('event_type', 'channel', 'is_active')
    search_fields = ('subject', 'body')


@admin.register(NotificationTrigger)
class NotificationTriggerAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'schedule', 'is_active', 'max_retries', 'created_at')
    list_filter = ('event_type', 'schedule', 'is_active')
    search_fields = ('name',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'channel', 'recipient', 'status', 'attempt_count', 'sent_at', 'created_at')
    list_filter = ('event_type', 'channel', 'status')
    search_fields = ('recipient', 'subject')
    readonly_fields = ('created_at',)
    
@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'habit_name', 'category', 'completed')
    list_filter = ('date', 'category', 'completed')
    search_fields = ('habit_name', 'notes')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'due_datetime', 'frequency', 'active')
    list_filter = ('frequency', 'active')
    search_fields = ('title', 'message')


@admin.register(MedicationLog)
class MedicationLogAdmin(admin.ModelAdmin):
    list_display = ('medication_name', 'dosage', 'status', 'taken_at', 'user')
    list_filter = ('status', 'taken_at')
    search_fields = ('medication_name', 'notes', 'side_effects')
    raw_id_fields = ('user', 'schedule')


@admin.register(MedicationInventory)
class MedicationInventoryAdmin(admin.ModelAdmin):
    list_display = ('medication_name', 'current_count', 'refill_reminder_threshold', 'expiration_date', 'needs_refill', 'user')
    list_filter = ('expiration_date',)
    search_fields = ('medication_name', 'pharmacy_name', 'notes')
    raw_id_fields = ('user', 'schedule')
