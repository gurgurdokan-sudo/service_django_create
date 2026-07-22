# Employee → Staff リファクタリングに伴う変更
#
# モデル名の変更自体は過去のマイグレーション（0001〜0003）をStaff表記に
# 書き換える方式で対応した（swappableモデルのRenameModelは同アプリ内FKが
# 解決できずfresh installで失敗するため）。
# DBテーブル名は db_table='employees_employee' で据え置きのため、
# 既存DBにはこのマイグレーション（can_delete追加と表示名変更）だけが適用される。
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0003_alter_employee_slack_user_id'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='staff',
            options={'verbose_name': 'スタッフ', 'verbose_name_plural': 'スタッフ'},
        ),
        migrations.AddField(
            model_name='staff',
            name='can_delete',
            field=models.BooleanField(
                default=False,
                help_text='ONのスタッフは各画面でデータの削除ができる。付与・剥奪は管理サイトからのみ行う',
                verbose_name='削除権限',
            ),
        ),
    ]
