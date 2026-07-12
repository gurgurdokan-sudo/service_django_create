from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Employee(AbstractUser):
    '''従業員（ログインユーザー）

    AUTH_USER_MODEL として使用する。dashboard.User（被保険者/利用者）とは別物なので注意。
    Slack連携: slack_user_id にSlackのメンバーID（U...）を設定すると
    出退勤ボタン・日報プロンプトの送信対象になる。
    '''
    slack_user_id = models.CharField(
        'SlackユーザーID', max_length=20, blank=True, default='',
        help_text='Slackプロフィール →「…」→「メンバーIDをコピー」で取得（例: U0A1E588J2J）',
    )
    name_kana = models.CharField('フリガナ', max_length=100, blank=True, default='')
    tel = models.CharField('電話番号', max_length=20, blank=True, default='')

    class Meta:
        verbose_name = '従業員'
        verbose_name_plural = '従業員'

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username


class Assignment(models.Model):
    '''勤怠スケジュール: その日、どの従業員がどの利用者を担当するか'''
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='従業員', related_name='assignments',
    )
    user = models.ForeignKey(
        'dashboard.User', on_delete=models.CASCADE,
        verbose_name='利用者', related_name='assignments',
    )
    date = models.DateField('日付')
    note = models.CharField('メモ', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        verbose_name = '担当スケジュール'
        verbose_name_plural = '担当スケジュール'
        ordering = ['-date', 'employee_id']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'user', 'date'],
                name='unique_employee_user_date',
            ),
        ]

    def __str__(self):
        return f'{self.date} {self.employee} → {self.user}'


class Attendance(models.Model):
    '''出退勤記録（Slackのボタン押下または画面から登録）'''
    class Kind(models.TextChoices):
        CLOCK_IN = 'in', '出勤'
        CLOCK_OUT = 'out', '退勤'

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='従業員', related_name='attendances',
    )
    date = models.DateField('日付')
    kind = models.CharField('種別', max_length=3, choices=Kind.choices)
    timestamp = models.DateTimeField('打刻時刻')

    class Meta:
        verbose_name = '出退勤記録'
        verbose_name_plural = '出退勤記録'
        ordering = ['-date', 'employee_id', 'kind']
        constraints = [
            # 同日同種の二重打刻を防ぐ（Slack側は既存があればスキップする想定）
            models.UniqueConstraint(
                fields=['employee', 'date', 'kind'],
                name='unique_employee_date_kind',
            ),
        ]

    def __str__(self):
        return f'{self.date} {self.employee} {self.get_kind_display()}'
