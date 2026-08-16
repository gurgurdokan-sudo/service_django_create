from django import template
from dashboard.excel.service_calculator import format_comma
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), "")
@register.filter
def total_count(plan, row_type):
    return plan.get_total_count(str(row_type))

@register.filter
def format_comma_temp(value):
    return format_comma(value)