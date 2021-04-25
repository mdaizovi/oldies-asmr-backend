from django.db import models
from django.utils import timezone

import re

from .model_managers import SongManager

class Song(models.Model):
    # Reminder: Jan 1 2022 anything before 192? becomes public domain
    title = models.CharField(max_length=255)
    other_title = models.CharField(max_length=255,null=True, blank=True)
    contributor_names = models.TextField(null=True, blank=True)
    genre = models.CharField(max_length=255,null=True, blank=True)

    recording_label = models.CharField(max_length=255,null=True, blank=True)
    recording_date = models.CharField(max_length=255,null=True, blank=True)
    recording_location = models.CharField(max_length=255,null=True, blank=True)
    recording_repository = models.CharField(max_length=255,null=True, blank=True)
    rights_advisory = models.CharField(max_length=255,null=True, blank=True)

    description_url = models.URLField(null=True, blank=True)
    streaming_url = models.URLField(null=True, blank=True)
    audio_file = models.FileField(null=True, blank=True, upload_to="songs/")

    citation_chicago = models.CharField(max_length=255,null=True, blank=True)
    citation_apa = models.CharField(max_length=255, null=True, blank=True)
    citation_mla = models.CharField(max_length=255, null=True, blank=True)

    # possibility to skip if song is terrible, or racist, or whatever. I guess could just delete...
    is_skipped = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    is_unique = models.BooleanField(default=True, help_text="True is no others have same title")
    public_domain = models.BooleanField(default=True, help_text="T if recorded prior to 1923")
    seconds = models.IntegerField(null=True, blank=True)

    objects = SongManager()

    def __str__(self):
        return "<{}> {} ({})".format(self.__class__.__name__, self.title, self.recording_date)


    def parse_streaming_filename(self):
        """
        returns something like ucsb_victor_73536_01_b26920_01
        """
        if self.streaming_url:
            bookend1 = "service:mbrsrs:mbrsjukebox:"
            bookend2="/full/"
            if all([bookend1 in self.streaming_url,bookend2 in self.streaming_url]):
                double = re.search(r'{}(.*?){}'.format(bookend1, bookend2), self.streaming_url).group(1)
                return double.split(":")[0]

    def parse_jukebox_id(self):
        """
        returns something like jukebox-718006
        """
        if self.description_url:
            return self.description_url.split("/")[-2]

class SongSkip(models.Model):
    help_text = "Event this song was skipped, possibly indicating user dislikes it"
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    skipped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "<{}> {} ({})".format(self.__class__.__name__, self.song, self.skipped_at.strftime("%Y-%m-%d %H:%M"))