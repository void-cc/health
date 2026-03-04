from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, PrivacyPreference


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = [
            'date_of_birth', 'biological_sex', 'height_cm',
            'genetic_baseline_info', 'avatar', 'theme_preference',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'biological_sex': forms.Select(attrs={'class': 'form-control'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Height in cm'}),
            'genetic_baseline_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'theme_preference': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email


class PrivacyPreferenceForm(forms.ModelForm):
    class Meta:
        model = PrivacyPreference
        fields = [
            'allow_data_sharing', 'allow_analytics',
            'allow_research_use', 'data_retention_days',
            'show_profile_publicly',
        ]
        widgets = {
            'data_retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '30'}),
        }


class AccountDeleteForm(forms.Form):
    confirm_text = forms.CharField(
        max_length=50,
        help_text='Type "DELETE" to confirm account deletion.',
    )

    def clean_confirm_text(self):
        text = self.cleaned_data.get('confirm_text', '')
        if text != 'DELETE':
            raise forms.ValidationError('You must type "DELETE" to confirm.')
        return text
