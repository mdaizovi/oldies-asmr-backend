from django.conf import settings
from rest_framework import serializers

from ..models import Song, SongSkip


class SongSerializer(serializers.ModelSerializer):

    class Meta:
        model = Song
        fields = ("id","title", "streaming_url", "citation_mla")


class SongSkipSerializer(serializers.ModelSerializer):

    class Meta:
        model = SongSkip
        fields = ("song",)