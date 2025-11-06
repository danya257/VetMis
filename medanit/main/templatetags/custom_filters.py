from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу. Если ключа нет, возвращает None."""
    return dictionary.get(key) if isinstance(dictionary, dict) else None
