class CsvValidator:
    """国保の仕様に従ってCSVを検証するクラス"""
    def validate(self, csv_text):
        self.check_length(csv_text)
        self.check_required(csv_text)
        self.check_encoding(csv_text)
