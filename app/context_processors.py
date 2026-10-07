from .permissions import user_role


def role(request):
    """Make the current user's role ('admin', 'doctor', 'patient' or None) available in templates."""
    return {'role': user_role(request.user)}
