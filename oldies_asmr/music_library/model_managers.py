from datetime import timedelta
import os 
import random

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
        print("------------\nstarting {}\n".format(sound_dict))
        sound_base_dir = '/Users/micheladaizovi/dev/reactnative/OldiesASMR/app/assets/audio/sounds/'
        qset = list(self.filter(public_domain=True, is_skipped=False, audio_file__isnull=False, seconds__isnull=False).order_by("?"))
        print("possible songs: {}".format(len(qset)))
        seconds_total = minutes*60
        seconds_cumulative = 0
        track_list = []
        print("Track List:\n________________________")
        while seconds_cumulative < seconds_total:
            s = random.choice(qset)
            qset.remove(s)
            track_list.append(s.audio_file.path) 
            print("{} - {} (ID: {})".format(s.recording_date, s.title, s.id))
            seconds_cumulative += s.seconds 
        print("________________________\n")
        mins = int(seconds_cumulative/60) 
        hrs = int(mins/60)
        print("{}: track list is done, {} songs. {} mins total, {} hours".format(
            timezone.now().strftime("%H:%M:%S"), len(track_list), mins, hrs))

        base_playlist = AudioSegment.empty()
        for songfile in track_list:
             base_playlist +=  AudioSegment.from_file(songfile)
        playlist_duration_in_milliseconds = len(base_playlist)
        print("{}: playlist is done".format(timezone.now().strftime("%H:%M:%S")))

        sound_list = []
        track_name = ""
        for sound_name, volume in sound_dict.items():
            track_name += "{}.{}_".format(sound_name, volume)
            sound_path = sound_base_dir + sound_name + ".mp3"
            sound_base = AudioSegment.from_file(sound_path)
            sound = sound_base + volume # volume may be 0 if no change is desired.
            sound_list.append(sound)
        print("{}: sound list is done".format(timezone.now().strftime("%H:%M:%S")))

        # Overlay all the sounds together so they can fade in together
        base_sound = AudioSegment.silent(duration=playlist_duration_in_milliseconds)
        sound_track = base_sound
        for s in sound_list:
            sound_track = sound_track.overlay(s, loop=True)
        sound_track = sound_track.fade_in(duration=20000)
        print("{}: soundtrack is done".format(timezone.now().strftime("%H:%M:%S")))

        # Now combine all sounds with song.
        base_track = base_playlist.overlay(sound_track, gain_during_overlay=5)
        print("{}: song and sounds combined".format(timezone.now().strftime("%H:%M:%S")))

        track = base_track.fade_out(duration=15000)
        if len(track_name)== 0:
            track_name = randomString()

        track_name += "{}mins".format(minutes) 
        track_name += ".mp3"
        export_location = os.path.join(settings.MEDIA_ROOT, "tracks", track_name)
        track.export(export_location, format="mp3")
        print("\n{}: done exporting {}\n-----------".format(timezone.now().strftime("%H:%M:%S"), track_name))

