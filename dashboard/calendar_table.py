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

def to_wareki(date: datetime.date) -> str:
    year = date.year
    for era_name, start_year in ERA_TABLE:
        if year >= start_year:
            era_year = year - start_year + 1
            return f"{era_name}{era_year}年{date.month}月{date.day}日"
    return f"{year}年{date.month}月{date.day}日"  # 明治以前は西暦のまま


def from_wareki(era_name: str, era_year: int, month: int, day: int) -> datetime.date:
    for name, start_year in ERA_TABLE:
        if name == era_name:
            year = start_year + era_year - 1
            return datetime.date(year, month, day)
    raise ValueError(f"不明な元号です: {era_name}")
