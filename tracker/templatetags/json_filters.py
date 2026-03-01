import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='tojson')
def tojson(value):
    return mark_safe(json.dumps(value))

@register.filter(name='lookup')
def lookup(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
