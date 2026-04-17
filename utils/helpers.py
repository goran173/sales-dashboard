import pandas as pd

def format_currency(value):
    """
    Formats a number as currency: $1,234.56
    """
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return value

def format_number(value):
    """
    Formats a number with commas: 1,234
    """
    try:
        return f"{value:,}"
    except (ValueError, TypeError):
        return value

def calculate_growth(current, previous):
    """
    Calculates percentage growth between current and previous values.
    Returns percentage change formatted as a string or decimal.
    """
    if previous == 0 or pd.isna(previous):
        return 0.0
    growth = ((current - previous) / previous) * 100
    return growth
