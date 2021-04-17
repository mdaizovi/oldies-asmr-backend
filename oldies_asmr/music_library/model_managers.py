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
        sound_base_dir = '/Users/micheladaizovi/dev/reactnative/OldiesASMR/app/assets/audio/sounds/'
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
        playlist_duration_in_milliseconds = len(base_playlist)

        sound_list = []
        for sound_name, volume in sound_dict.items():
            sound_path = sound_base_dir + sound_name + ".mp3"
            sound_base = AudioSegment.from_file(sound_path)
            sound = sound_base + volume # volume may be 0 if no change is desired.
            sound_list.append(sound)
        
        # Overlay all the sounds togeter so they can fade in together
        base_sound = AudioSegment.silent(duration=playlist_duration_in_milliseconds)
        sound_track = base_sound
        for s in sound_list:
            # sound_track = sound_track.overlay(s, loop=True, gain_during_overlay=-10)
            sound_track = sound_track.overlay(s, loop=True)
        sound_track = sound_track.fade_in(duration=20000)
        
        # Now combine all sounds with song.
        base_track = base_playlist.overlay(sound_track)

        track = base_track.fade_out(duration=10000)
        track_name = "{}.mp3".format(randomString())
        export_location = os.path.join(settings.MEDIA_ROOT, "tracks", track_name)
        track.export(export_location, format="mp3")
        print("done exporting {}".format(track_name))

