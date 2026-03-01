import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Characters that could break out of a <script> context
_json_escapes = {
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
}

@register.filter(name='tojson')
def tojson(value):
    s = json.dumps(value)
    return mark_safe(s.translate(_json_escapes))

@register.filter(name='lookup')
def lookup(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
