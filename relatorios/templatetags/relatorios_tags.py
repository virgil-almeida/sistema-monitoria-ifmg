from django import template

register = template.Library()


@register.filter
def minutos_horas(minutos):
    if not minutos:
        return "—"
    h = minutos // 60
    m = minutos % 60
    if h and m:
        return f"{h}h {m}min"
    if h:
        return f"{h}h"
    return f"{m}min"
