from django.contrib import admin

# Register your models here.
from .models import*

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    search_fields = ["audio_file", "title", "contributor_names"]

@admin.register(SongSkip)
class SongSkipAdmin(admin.ModelAdmin):
    search_fields = ["song_title"]