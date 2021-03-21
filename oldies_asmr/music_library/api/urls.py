from django.urls import re_path

from .views import SongPlayListAPIView

urlpatterns = [
    re_path(
        r"^playlist/?$",
        SongPlayListAPIView.as_view(),
        name="song-playlist",
    ),

]
