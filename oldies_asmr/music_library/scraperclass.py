import requests
import bs4
from collections import OrderedDict
from time import sleep, time
from random import randint, choice
import os
import tempfile

from django.core import files
from django.forms.models import model_to_dict

from .models import Song

#===============================================================================
class Scraper():

    def __init__(self, *args, **kwargs):
        # Just ragtime and jazz, 1,022 items: https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more
        #self.base_url = "https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more"
        # Prior to 1923, 454 items: (soon to be public domain):
        self.base_url = "https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more&end_date=1922-12-31&searchType=advanced&start_date=1900-01-01"
        self.content = None
        # for other pages add &sp=2, done in increments of 25.
        # 19 pges for pub domain, 41 for other

    #---------------------------------------------------------------------------
    def build_url(self, p=1):
        print("\n\n---{}---\n\n".format(p))
        return "{}&sp={}".format(self.base_url, p)

    #---------------------------------------------------------------------------
    def req_url(self, url = None):
        """Takes full_url, returns site reading for Beautiful Soup, using requests"""
        attempts = 0
        response = None
        if not url:
            url = self.base_url

        while not response and attempts < 5:
            try:
                attempts += 1
                response = requests.get(url,timeout=300)
                if response:
                    print("got response via requests")
                    self.content = response.text
                    break
            except:
                if attempts > 5:
                    break
                sleep_int = randint(5,10)
                sleep(sleep_int)

        return self.content

    def title_to_snake(self, title):
        return title.lower().replace(" ", "_")

    def parse_list_response(self):
        soup = bs4.BeautifulSoup(self.content, "html.parser")
        results = soup.find(id='results')
        items = results.find_all("li", {"class": "item"})
        for i in items:
            desc_elem = i.find('div', class_='description')
            item_desc = desc_elem.find('div', class_='item-description')
            item_desc_span = item_desc.find('span', class_='item-description-title')
            item_url = item_desc_span.find('a')

            description_url = item_url['href']
            title = item_url.text.strip()
            print("\n{}\n".format(title)) # i think title is sometimes too much gunk
            Song.objects.get_or_create(title=title, description_url=description_url)

    def parse_item_response(self):
        soup = bs4.BeautifulSoup(self.content, "html.parser")
        media_elem = soup.find('div', class_='audio-player-wrapper')
        source_elem = media_elem.find(attrs={"src": True})
        streaming_url = source_elem['src']

        citation_div = soup.find(id='cite-this-content')
        citation_chicago_div = citation_div.find('div', class_='chicago-citation')
        citation_chicago = citation_chicago_div.find('p').text.strip()

    def get_song_info(self, song):
        print("\n--------")
        self.content = self.req_url(url = song.description_url)
        soup = bs4.BeautifulSoup(self.content, "html.parser")
        media_elem = soup.find('div', class_='audio-player-wrapper')
        source_elem = media_elem.find(attrs={"src": True})
        streaming_url = source_elem['src']
        song.streaming_url = streaming_url

        citation_div = soup.find(id='cite-this-content')
        for classname, attr in {"chicago-citation":"citation_chicago", "mla-citation":"citation_mla", "apa-citation":"citation_apa"}.items():
            citation_type_div = citation_div.find('div', class_=classname)
            citation = citation_type_div.find('p').text.strip()
            setattr(song, attr, citation)

        table = soup.find(id='item-cataloged-data')
        content_list = [tag.text for tag in table.find_all()]
        ct = []
        for c in content_list:
            text = c.replace('\n', '').strip()
            ct.append(text)
        dd_keys_raw = [tag.text for tag in table.find_all("dt")]
        dd_keys = []
        for d in dd_keys_raw:
            text = d.replace('\n', '').strip()
            dd_keys.append(text)
        for i in ct:
            if i in dd_keys:
                current_title_index = dd_keys.index(i)
                current_content_index = ct.index(i)
                if current_title_index+1 != len(dd_keys):
                    next_title = dd_keys[current_title_index+1]
                    next_title_index = ct.index(next_title)
                    item_list = ct[current_content_index+1:next_title_index]
                    item = ", ".join(item_list)
                    setattr(song, self.title_to_snake(i), item)
        song.save()
        print(model_to_dict(song))
        print("--------\n")

    def download_mp3(self, song_qset):
        with requests.Session() as req:
            i = 0
            for s in song_qset:
                i+=1
                print("\n\n{}.".format(i))
                name = s.parse_jukebox_id()
                file_name = name + ".mp3"
                print("Downloading File {}".format(name))
                download = req.get(s.streaming_url)
                with open(file_name, 'wb') as f:
                    f.write(download.content)
                    s.audio_file.save(
                        os.path.basename(file_name), files.File(open(file_name, "rb"))
                    )
                os.remove(file_name)




