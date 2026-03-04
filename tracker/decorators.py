import functools

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def staff_only(view_func):
    """Decorator that requires the user to be logged in and have staff privileges.

    Non-staff users receive a 403 Forbidden response.  This is used to gate
    legacy CRUD views so that only staff / admin users can access them.
    """
    @login_required
    @functools.wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
