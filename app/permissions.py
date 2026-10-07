"""Who is allowed to see which page.

Every account has exactly one role:

- admin    a superuser, or a member of the "admin" group
- doctor   a member of the "doctor" group, with an approved DOCTOR profile
- patient  a member of the "patient" group, with an approved USER profile

Views declare who may use them with @role_required(...). Anonymous visitors
are sent to the login page; logged-in users with the wrong role get a 403.
Doctor and patient accounts are re-checked on every request, so an account
that is rejected after logging in loses access straight away.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

ADMIN = 'admin'
DOCTOR = 'doctor'
PATIENT = 'patient'

ADMIN_GROUP = 'admin'
DOCTOR_GROUP = 'doctor'
PATIENT_GROUP = 'patient'

APPROVED = 'Approved'


def user_role(user):
    """Return 'admin', 'doctor', 'patient', or None for anonymous/unknown accounts."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMIN
    groups = set(user.groups.values_list('name', flat=True))
    if ADMIN_GROUP in groups:
        return ADMIN
    if DOCTOR_GROUP in groups:
        return DOCTOR
    if PATIENT_GROUP in groups:
        return PATIENT
    return None


def role_profile(user, role):
    """The DOCTOR or USER profile behind a doctor/patient account (None for admins)."""
    from .models import DOCTOR as DoctorProfile
    from .models import USER as PatientProfile

    if role == DOCTOR:
        return DoctorProfile.objects.filter(user_id=user).first()
    if role == PATIENT:
        return PatientProfile.objects.filter(user_id=user).first()
    return None


def is_approved(user, role):
    if role == ADMIN:
        return True
    profile = role_profile(user, role)
    return profile is not None and profile.Approval_Status == APPROVED


def role_required(*allowed):
    """Allow a view only for the given roles, e.g. @role_required(ADMIN, DOCTOR)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            role = user_role(request.user)
            if role not in allowed:
                raise PermissionDenied
            if not is_approved(request.user, role):
                logout(request)
                messages.error(request, 'Your account is not approved. Please contact the administrator.')
                return redirect('login')
            request.role = role
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


HOME_FOR_ROLE = {ADMIN: 'adminindex', DOCTOR: 'doctor_home', PATIENT: 'user_home'}
