# home/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def station_in_address(report_address, station_name):
    """
    Checks if the key part (first word) of station_name appears in report_address.
    Returns True if found, otherwise False.
    """
    if not report_address or not station_name:
        return False
    # Use the first word of the station name as the key substring
    key = station_name.split()[0]
    return key.lower() in report_address.lower()
