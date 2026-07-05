from django.contrib import admin

from .models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'title', 'mood', 'updated_at']
    list_filter = ['mood', 'date']
    search_fields = ['title', 'body']
