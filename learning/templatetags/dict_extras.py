from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """
    Template helper: safely get dict[key] in templates.
    Usage: progress_map|get_item:lesson.id
    """
    try:
        return d.get(key)
    except Exception:
        return None