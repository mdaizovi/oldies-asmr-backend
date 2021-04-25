import os
import random

from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from ..api.serializers import SongSerializer, SongSkipSerializer
from ..models import Song, SongSkip


class SongPlayListAPIView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SongSerializer

    def get_queryset(self):
        return Song.objects.exclude(streaming_url=None, is_skipped=True)


    def get(self, request, format=None):
        songs = [s for s in self.get_queryset()]
        # Note that shuffle works in place, and returns None.
        random.shuffle(songs)
        return Response(data=self.serializer_class(songs, many=True).data, status=status.HTTP_200_OK)


class SongSkipCreateAPIView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SongSkipSerializer
    queryset = SongSkip.objects.all()

    # def post(self, request):
    #     serializer = self.get_serializer(data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)