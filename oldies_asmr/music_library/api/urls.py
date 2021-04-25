from django.urls import re_path

from .views import SongPlayListAPIView, SongSkipCreateAPIView

urlpatterns = [
    re_path(
        r"^playlist/?$",
        SongPlayListAPIView.as_view(),
        name="song-playlist",
    ),
    re_path(
        r"^skip/?$",
        SongSkipCreateAPIView.as_view(),
        name="song-skip",
    ),

]
