from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), "")
@register.filter
def total_count(plan, row_type):
    return plan.get_total_count(str(row_type))