from django import template

register = template.Library()


@register.filter
def get(mapping, key):
    """{{ values|get:name }}: look a field up by a name held in a variable."""
    try:
        return mapping.get(key, '') or ''
    except AttributeError:
        return ''
