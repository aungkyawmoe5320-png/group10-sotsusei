from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """辞書から、変数のキーで値を取り出す（テンプレートでは form[q.key] と書けないため）。"""
    return mapping.get(key, "")