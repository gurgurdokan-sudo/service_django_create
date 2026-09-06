import csv
import os
from django.conf import settings

class CsvExporter:
    def __init__(self, headers):
        self.headers = headers

    def export(self, rows, year, month):
        filename = f"kokuho_{year}_{month}.csv"
        csv_path = os.path.join(settings.MEDIA_ROOT, filename)

        with open(csv_path, "w", newline="", encoding="shift_jis") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(rows)

        return csv_path
