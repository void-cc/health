import io
import base64

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils import timezone

from .models import UserProfile, SecurityLog, UserSession, PrivacyPreference
from .forms import RegistrationForm, UserProfileForm, PrivacyPreferenceForm, AccountDeleteForm


def _get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _get_device_type(user_agent):
    """Simple device type detection from user agent string."""
    ua = user_agent.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'Mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        return 'Tablet'
    return 'Desktop'


def _log_security_event(user, action, request):
    """Create a security log entry."""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    SecurityLog.objects.create(
        user=user,
        action=action,
        ip_address=_get_client_ip(request),
        user_agent=user_agent,
        device_type=_get_device_type(user_agent),
    )


def _track_session(user, request):
    """Create or update a session tracking entry."""
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    UserSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'ip_address': _get_client_ip(request),
            'user_agent': user_agent,
            'device_type': _get_device_type(user_agent),
            'last_activity': timezone.now(),
            'is_active': True,
        }
    )


def register_view(request):
    """User registration with email and password."""
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile and privacy preferences
            UserProfile.objects.create(user=user)
            PrivacyPreference.objects.create(user=user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            _log_security_event(user, 'login', request)
            _track_session(user, request)
            messages.success(request, 'Registration successful! Welcome to Health Tracker.')
            return redirect('index')
    else:
        form = RegistrationForm()
    return render(request, 'account/register.html', {'form': form})


def login_view(request):
    """Standard email/password login."""
    if request.user.is_authenticated:
        return redirect('index')
    timeout = request.GET.get('timeout')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Check if MFA is enabled
            if _user_has_totp(user):
                # Store user_id in session for MFA verification
                request.session['mfa_user_id'] = user.pk
                return redirect('mfa_verify')
            login(request, user)
            _log_security_event(user, 'login', request)
            _track_session(user, request)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('index')
        else:
            # Log failed login if username exists
            username = request.POST.get('username', '')
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(username=username)
                _log_security_event(user, 'login_failed', request)
            except User.DoesNotExist:
                pass
    else:
        form = AuthenticationForm()
    return render(request, 'account/login.html', {'form': form, 'timeout': timeout})


def logout_view(request):
    """Logout and clean up session."""
    if request.user.is_authenticated:
        _log_security_event(request.user, 'logout', request)
        session_key = request.session.session_key
        if session_key:
            UserSession.objects.filter(session_key=session_key).update(is_active=False)
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


@login_required
def profile_view(request):
    """View and edit user profile."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            # Update User model fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            _log_security_event(request.user, 'profile_updated', request)
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    return render(request, 'account/profile.html', {'form': form, 'profile': profile})


@login_required
def change_password_view(request):
    """Change password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            _log_security_event(user, 'password_changed', request)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'account/change_password.html', {'form': form})


@login_required
def security_log_view(request):
    """View security activity log."""
    logs = SecurityLog.objects.filter(user=request.user)[:50]
    return render(request, 'account/security_log.html', {'logs': logs})


@login_required
def active_sessions_view(request):
    """View and manage active sessions."""
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    current_session_key = request.session.session_key
    return render(request, 'account/active_sessions.html', {
        'sessions': sessions,
        'current_session_key': current_session_key,
    })


@login_required
def terminate_session_view(request, session_id):
    """Terminate a specific session."""
    if request.method == 'POST':
        session = get_object_or_404(UserSession, pk=session_id, user=request.user)
        session.is_active = False
        session.save()
        # Delete the Django session
        from django.contrib.sessions.models import Session
        try:
            Session.objects.get(session_key=session.session_key).delete()
        except Session.DoesNotExist:
            pass
        messages.success(request, 'Session terminated.')
    return redirect('active_sessions')


@login_required
def privacy_preferences_view(request):
    """Manage privacy preferences."""
    prefs, _ = PrivacyPreference.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PrivacyPreferenceForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            messages.success(request, 'Privacy preferences updated.')
            return redirect('privacy_preferences')
    else:
        form = PrivacyPreferenceForm(instance=prefs)
    return render(request, 'account/privacy_preferences.html', {'form': form})


@login_required
def delete_account_view(request):
    """Self-service account deletion."""
    if request.method == 'POST':
        form = AccountDeleteForm(request.POST)
        if form.is_valid():
            user = request.user
            _log_security_event(user, 'account_deleted', request)
            # Deactivate all sessions
            UserSession.objects.filter(user=user).update(is_active=False)
            logout(request)
            # Delete the user (cascades to profile, logs, etc.)
            user.delete()
            messages.success(request, 'Your account and all data have been permanently deleted.')
            return redirect('login')
    else:
        form = AccountDeleteForm()
    return render(request, 'account/delete_account.html', {'form': form})


# --- MFA / TOTP Views ---

def _user_has_totp(user):
    """Check if user has TOTP device configured."""
    try:
        from django_otp.plugins.otp_totp.models import TOTPDevice
        return TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    except Exception:
        return False


@login_required
def mfa_setup_view(request):
    """Set up TOTP MFA."""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    import qrcode
    import qrcode.image.svg

    # Check if user already has a confirmed device
    existing_device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if existing_device:
        messages.info(request, 'MFA is already enabled. Disable it first to set up a new device.')
        return redirect('profile')

    # Create or get unconfirmed device
    device, created = TOTPDevice.objects.get_or_create(
        user=request.user,
        confirmed=False,
        defaults={'name': f'{request.user.username}-totp'}
    )

    if request.method == 'POST':
        token = request.POST.get('token', '')
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            _log_security_event(request.user, 'mfa_enabled', request)
            messages.success(request, 'MFA has been enabled successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

    # Generate QR code
    totp_url = device.config_url
    qr = qrcode.make(totp_url, image_factory=qrcode.image.svg.SvgImage)
    buffer = io.BytesIO()
    qr.save(buffer)
    qr_svg = buffer.getvalue().decode('utf-8')

    return render(request, 'account/mfa_setup.html', {
        'qr_svg': qr_svg,
        'secret_key': base64.b32encode(device.bin_key).decode('utf-8'),
    })


def mfa_verify_view(request):
    """Verify TOTP token during login."""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django.contrib.auth.models import User

    user_id = request.session.get('mfa_user_id')
    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        token = request.POST.get('token', '')
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device and device.verify_token(token):
            del request.session['mfa_user_id']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            _log_security_event(user, 'login', request)
            _track_session(user, request)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('index')
        else:
            messages.error(request, 'Invalid verification code.')

    return render(request, 'account/mfa_verify.html')


@login_required
def mfa_disable_view(request):
    """Disable MFA."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    if request.method == 'POST':
        TOTPDevice.objects.filter(user=request.user).delete()
        _log_security_event(request.user, 'mfa_disabled', request)
        messages.success(request, 'MFA has been disabled.')
        return redirect('profile')

    return render(request, 'account/mfa_disable.html')
