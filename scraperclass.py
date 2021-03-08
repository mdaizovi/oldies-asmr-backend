
import requests
import bs4
import mechanize
from time import sleep, time
from random import randint, choice
import os

#===============================================================================
class Scraper():

    def __init__(self, *args, **kwargs):
        self.full_url = ""
        self.content = None


    #---------------------------------------------------------------------------
    def req_url(self, url = None):
        """Takes full_url, returns site reading for Beautiful Soup, using requests"""
        attempts = 0
        response = None
        if not url:
            url = self.full_url

        while not response and attempts < 5:
            try:
                attempts += 1
                print("req attempts: ",attempts)
                response = requests.get(url,timeout=300)
                if response:
                    print "got response via requests"
                    self.content = response.text
                    break
            except:
                if attempts > 5:
                    break
                sleep_int = randint(5,10)
                sleep(sleep_int)

        return self.content
