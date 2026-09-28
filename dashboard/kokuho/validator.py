from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def validate_year_month(value):
    value = str(value)
    if len(value) != 6:
        return False
    if not value.isdigit():
        return False
    try:
        datetime.strptime(value, "%Y%m")
    except ValueError:
        return False
    return True

class ClaimValidator:
    """
    国保連請求データの検証を行うクラス
    """
    def validate(self, rows):
        office_number = 0
        if not rows:
            logger.error("請求対象のデータがありません。")

        for index, row in enumerate(rows):
            current_row = row[index]
            if current_row[0]==1: #事業所ヘッダー
                office_number = current_row[7]
                if validate_year_month(current_row[10]):
                    logger.error('日付フォーマットでエラー')
            if current_row[0]==2:
                if office_number == 0:
                    logger.error('事業所ヘッダー行がない')
                if current_row[2]==7111:
                    if validate_year_month(current_row[3]):
                        logger.error('日付フォーマットでエラー')
                    if current_row[4]!=office_number:
                        logger.error('office_numberが出力列でエラー')

        return True