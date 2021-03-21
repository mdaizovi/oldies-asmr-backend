import os
import random

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from ..api.serializers import SongSerializer
from ..models import Song


class SongPlayListAPIView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SongSerializer

    def get_queryset(self):
        return Song.objects.exclude(streaming_url=None, is_skipped=True)


    def get(self, request, format=None):
        songs = [s for s in self.get_queryset()]
        # Note that shuffle works in place, and returns None.
        random.shuffle(songs)
        return Response(data=self.serializer_class(songs, many=True).data, status=status.HTTP_200_OK)
