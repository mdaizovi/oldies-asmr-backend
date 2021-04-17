from datetime import timedelta
import os 

from django.conf import settings
from django.contrib.auth.models import UserManager
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Manager, Q
from django.utils import timezone
from pydub import AudioSegment

from misc.utils import randomString

class SongManager(Manager):

    def create_mp3(self, minutes=570, sound_dict={}):
        """
        Creates an Mp3 of approximately X minutes (will go over due to song length). 
        Default is 9.5 hours
        sound_dict has k,v of sound file path, and desired volume.
        """
        qset = self.filter(public_domain=True, is_skipped=False, audio_file__isnull=False, seconds__isnull=False).order_by("?")
        seconds_total = minutes*60
        seconds_cumulative = 0
        track_list = []
        for s in qset:
            if seconds_cumulative < seconds_total:
                track_list.append(s.audio_file.path) 
                seconds_cumulative += s.seconds 
            else:
                break 
        
        base_playlist = AudioSegment.empty()
        for songfile in track_list:
             base_playlist +=  AudioSegment.from_file(songfile)


        track = base_playlist
        

        track.fade_out(duration=5000))
        track_name = "{}.mp3".format(randomString())
        export_location = os.path.join(settings.MEDIA_ROOT, "tracks", track_name)
        base_playlist.export(export_location, format="mp3")
        print("done exporting {}".format(track_name))

