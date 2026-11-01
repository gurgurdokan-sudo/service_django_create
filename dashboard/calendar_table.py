import calendar
import datetime
import jpholiday

def get_month_days(year, month):
    cal = calendar.monthcalendar(year, month)
    days = []

    for week in cal:
        for day in week:
            if day == 0:
                continue

            date = datetime.date(year, month, day)
            days.append({
                "day": day,
                "weekday": date.weekday(),  
                "weekday_jp": "月火水木金土日"[date.weekday()],
                "is_sun": date.weekday() == 6,
                "is_sat": date.weekday() == 5,
                "is_holiday": jpholiday.is_holiday(date),
                "holiday_name": jpholiday.is_holiday_name(date),
            })
    return days
ERA_TABLE = [
    ("令和", 2019),
    ("平成", 1989),
    ("昭和", 1926),
    ("大正", 1912),
]

def _to_wareki_parts(value):
    for era_name, start_date in ERA_START_DATES:
        if value >= start_date:
            return era_name, value.year - start_date.year + 1
    raise ValueError(f"和暦に変換できない日付です: {value}")


def _format_wareki_date(value):
    era_name, era_year = _to_wareki_parts(value)
    return f"{era_name}{era_year}年{value.month}月{value.day}日"