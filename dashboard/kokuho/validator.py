# dashboard/kokuho/validator.py

class ValidationError(Exception):
    """国保連請求データの検証エラー"""
    pass


class ClaimValidator:

    def validate(self, rows):
        errors = []

        if not rows:
            errors.append("請求対象のデータがありません。")

        for index, row in enumerate(rows, start=1):

            # 事業所番号
            office_number = row.get("事業所番号")
            if not office_number:
                errors.append(
                    f"{index}行目: 事業所番号がありません。"
                )

            # サービス提供年月
            service_month = row.get("サービス提供年月")
            if not service_month:
                errors.append(
                    f"{index}行目: サービス提供年月がありません。"
                )
            elif len(str(service_month)) != 6:
                errors.append(
                    f"{index}行目: サービス提供年月が不正です。"
                )

            # 保険者番号
            insurer_number = row.get("保険者番号")
            if not insurer_number:
                errors.append(
                    f"{index}行目: 保険者番号がありません。"
                )

            # 被保険者番号
            insured_number = row.get("被保険者番号")
            if not insured_number:
                errors.append(
                    f"{index}行目: 被保険者番号がありません。"
                )

            # サービスコード
            service_code = row.get("サービスコード")
            if not service_code:
                errors.append(
                    f"{index}行目: サービスコードがありません。"
                )

            # 回数
            count = row.get("サービス提供回数")
            if count is None:
                errors.append(
                    f"{index}行目: サービス提供回数がありません。"
                )
            elif count < 0:
                errors.append(
                    f"{index}行目: サービス提供回数が負数です。"
                )

            # 単位数
            units = row.get("単位数")
            if units is None:
                errors.append(
                    f"{index}行目: 単位数がありません。"
                )
            elif units < 0:
                errors.append(
                    f"{index}行目: 単位数が負数です。"
                )

            # 金額
            benefit = row.get("請求額")
            public = row.get("公費")
            user_share = row.get("本人負担")

            if benefit is None:
                errors.append(
                    f"{index}行目: 請求額がありません。"
                )

            if public is None:
                errors.append(
                    f"{index}行目: 公費がありません。"
                )

            if user_share is None:
                errors.append(
                    f"{index}行目: 本人負担がありません。"
                )

            # 金額のマイナスチェック
            for field_name, value in [
                ("請求額", benefit),
                ("公費", public),
                ("本人負担", user_share),
            ]:
                if value is not None and value < 0:
                    errors.append(
                        f"{index}行目: {field_name}が負数です。"
                    )

        if errors:
            raise ValidationError("\n".join(errors))

        return True