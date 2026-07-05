from django.db import models
from django.urls import reverse
from dashboard.models import User

class Entry(models.Model):
    class Mood(models.TextChoices):
        GREAT = 'great', '😄 最高'
        GOOD = 'good', '🙂 良い'
        NORMAL = 'normal', '😐 普通'
        BAD = 'bad', '😞 いまいち'
        TERRIBLE = 'terrible', '😢 最悪'

    user = models.ForeignKey(User, verbose_name='利用者',on_delete=models.CASCADE)
    title = models.CharField(verbose_name='タイトル', max_length=200)
    body = models.TextField(verbose_name='本文')
    date = models.DateField(verbose_name='日付')
    mood = models.CharField(
        verbose_name='気分', max_length=10, choices=Mood.choices, default=Mood.NORMAL
    )
    image = models.ImageField(
        verbose_name='画像', upload_to='diary_images/%Y/%m/', blank=True, null=True
    )
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    slack_ts = models.CharField(
        'Slackメッセージts', max_length=32, unique=True,
        blank=True, null=True, editable=False,
        help_text='Slackから取り込んだメッセージの重複防止用ID',
    )

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = '日報'
        verbose_name_plural = '日報'

    def __str__(self):
        return f'{self.date} {self.title}'

    def get_absolute_url(self):
        return reverse('diary:detail', kwargs={'pk': self.pk})
