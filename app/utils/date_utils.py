from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Tuple, Any
from dateutil import parser


def parse_datetime(val: Any) -> Optional[datetime]:
    """
    Safely parse various datetime representations into a datetime object.
    Supports ISO formats, dates with times, Unix timestamps, etc.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, time.min)

    val_str = str(val).strip()
    if not val_str:
        return None

    try:
        # dateutil parser handles ISO8601, 'YYYY-MM-DD', 'DD/MM/YYYY', etc.
        dt = parser.parse(val_str)
        # If naive, leave naive or ensure uniform handling
        return dt
    except (ValueError, TypeError, OverflowError):
        return None


def parse_date(val: Any) -> Optional[date]:
    """Safely parse input into a date object."""
    dt = parse_datetime(val)
    return dt.date() if dt else None


def get_start_of_day(d: date) -> datetime:
    """Return start of day datetime (00:00:00)."""
    return datetime.combine(d, time.min)


def get_end_of_day(d: date) -> datetime:
    """Return end of day datetime (23:59:59.999999)."""
    return datetime.combine(d, time.max)


def get_week_bounds(d: date) -> Tuple[date, date]:
    """Return Monday (start) and Sunday (end) dates for the week containing d."""
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_month_bounds(year: int, month: int) -> Tuple[date, date]:
    """Return first and last date of given year and month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def generate_date_range(start_d: date, end_d: date) -> List[date]:
    """Generate all dates between start_d and end_d inclusive."""
    delta = (end_d - start_d).days
    return [start_d + timedelta(days=i) for i in range(max(0, delta + 1))]
