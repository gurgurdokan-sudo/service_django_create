class CsvExporter:
    """請求の仕様に従ってCSVを出力するクラス"""
    def serialize(self, claim_document):
        lines = []
        lines.append(self.serialize_basic(claim_document.basic))
        for d in claim_document.details:
            lines.append(self.serialize_detail(d))
        lines.append(self.serialize_summary(claim_document.summary))
        return "\n".join(lines)
def export_csv(csv_text, year, month):
    """ CSVをファイルに出力する関数 """
    filename = f"kokuho_{year}_{month}.csv"
    path = f"/tmp/{filename}"
    with open(path, "w", encoding="shift_jis") as f:
        f.write(csv_text)
    return path
