import calendar
from datetime import date
import jpholiday
# 元号の開始日。年だけで判定すると昭和元年・平成元年などの境目でずれる。
ERA_START_DATES = (
    ("令和", date(2019, 5, 1)),
    ("平成", date(1989, 1, 8)),
    ("昭和", date(1926, 12, 25)),
    ("大正", date(1912, 7, 30)),
    ("明治", date(1868, 1, 25)),
)

def get_month_days(year, month):
    cal = calendar.monthcalendar(year, month)
    days = []

    for week in cal:
        for day in week:
            if day == 0:
                continue

            w_date = date(year, month, day)
            days.append({
                "day": day,
                "weekday": w_date.weekday(),
                "weekday_jp": "月火水木金土日"[date.weekday()],
                "is_sun": w_date.weekday() == 6,
                "is_sat": w_date.weekday() == 5,
                "is_holiday": jpholiday.is_holiday(w_date),
                "holiday_name": jpholiday.is_holiday_name(w_date),
            })
    return days
ERA_TABLE = [
    ("令和", 2019),
    ("平成", 1989),
    ("昭和", 1926),
    ("大正", 1912),
]

def to_wareki_parts(value):
    for era_name, start_date in ERA_START_DATES:
        if value >= start_date:
            return era_name, value.year - start_date.year + 1
    raise ValueError(f"和暦に変換できない日付です: {value}")


def format_wareki_date(value):
    era_name, era_year = to_wareki_parts(value)
    return f"{era_name}{era_year}年{value.month}月{value.day}日"