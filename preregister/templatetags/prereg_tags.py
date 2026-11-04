from django import template
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag
def care_stars(level, with_text=False):
    """Show the care level as marks (same look as the care_app_4 prototype).
    要介護1-5: filled ★ out of 5 (yellow) / 要支援1-2: filled ● out of 2 (blue)"""
    n = int(level[-1]) if level and level[-1].isdigit() else 0
    if level.startswith("要支援"):
        kind, total, color = "circle", 2, "text-primary"
    else:
        kind, total, color = "star", 5, "text-warning"
    marks = format_html_join(
        "", '<i class="bi bi-{}"></i>', ((kind + ("-fill" if i < n else ""),) for i in range(total))
    )
    text = format_html('<span class="ms-2 small text-muted">{}</span>', level) if with_text else ""
    return format_html(
        '<span class="{} text-nowrap" role="img" aria-label="{}" title="{}">{}</span>{}',
        color, level, level, marks, text,
    )