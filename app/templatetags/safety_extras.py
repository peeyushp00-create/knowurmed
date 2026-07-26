from django import template

register = template.Library()

STATUS_CSS = {
    'general_info': 'bg-secondary',
    'low_concern': 'bg-success',
    'caution': 'bg-warning text-dark',
    'important_warning': 'bg-danger',
    'review_required': 'bg-primary',
    'unavailable': 'bg-light text-muted border',
}

STATUS_ICON = {
    'general_info': 'bi-info-circle',
    'low_concern': 'bi-check-circle',
    'caution': 'bi-exclamation-triangle',
    'important_warning': 'bi-exclamation-octagon',
    'review_required': 'bi-people',
    'unavailable': 'bi-question-circle',
}


@register.filter
def status_css(status):
    return STATUS_CSS.get(status, 'bg-secondary')


@register.filter
def status_icon(status):
    return STATUS_ICON.get(status, 'bi-info-circle')


@register.filter
def or_unavailable(value):
    return value if value else "Information unavailable"


@register.filter
def overall_safety_summary(notes):
    statuses = [n.status for n in notes.all()] if hasattr(notes, 'all') else [n.status for n in notes]
    if not statuses:
        return "Unable to complete the safety review"
    if any(s in ('important_warning', 'review_required') for s in statuses):
        return "Healthcare review recommended"
    if any(s == 'caution' for s in statuses):
        return "One or more cautions detected"
    return "No major warning found in available data"


@register.filter
def overall_safety_css(notes):
    summary = overall_safety_summary(notes)
    return {
        "Unable to complete the safety review": "bg-light text-muted border",
        "Healthcare review recommended": "bg-primary",
        "One or more cautions detected": "bg-warning text-dark",
        "No major warning found in available data": "bg-success",
    }[summary]
