from django.db import models

# Create your models here.
# ===============================================================================
class Song(models.Model):
    title = models.CharField(max_length=255)
    other_title = models.CharField(max_length=255,null=True, blank=True)
    contributor_names = models.TextField(null=True, blank=True)
    genre = models.CharField(max_length=255,null=True, blank=True)

    recording_label = models.CharField(max_length=255,null=True, blank=True)
    recording_date = models.CharField(max_length=255,null=True, blank=True)
    recording_location = models.CharField(max_length=255,null=True, blank=True)
    recording_repository = models.CharField(max_length=255,null=True, blank=True)
    rights_advisory = models.CharField(max_length=255,null=True, blank=True)

    streaming_url = models.URLField(null=True, blank=True)
    audio_file = models.FileField(null=True, blank=True, upload_to="songs/")