from django.conf import settings
from rest_framework import serializers

from ..models import Song


class SongSerializer(serializers.ModelSerializer):

    class Meta:
        model = Song
        fields = ("title", "streaming_url", "citation_mla")

