import requests
import bs4
from time import sleep, time
from random import randint, choice
import os
from .models import Song
#===============================================================================
class Scraper():

    def __init__(self, *args, **kwargs):
        # Just ragtime and jazz, 1,022 items: https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more
        self.base_url = "https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more"
        # Prior to 1923, 454 items: (soon to be public domain):
        # https://www.loc.gov/collections/national-jukebox/?fa=subject%3Aragtime%2C+jazz%2C+and+more&end_date=1922-12-31&searchType=advanced&start_date=1900-01-01
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
                print("req attempts: ",attempts)
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


