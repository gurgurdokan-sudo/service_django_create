import csv
import os
from django.conf import settings

class CsvExporter:
    @staticmethod
    def export(rows, year, month):
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        filename = f"kokuho_{year}_{month:02d}.csv"
        csv_path = os.path.join(settings.MEDIA_ROOT, filename)

        with open(csv_path, "w", newline="", encoding="shift_jis") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        return csv_path
