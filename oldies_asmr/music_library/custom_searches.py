#!/usr/bin/python
# -*- coding: utf-8-*-
#makes umlauts work: https://www.python.org/dev/peps/pep-0263/

import bs4
import re
import string
import urlparse

from decimal import Decimal
from random import randint
from time import sleep, time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


from .scraperclass import Scraper
from .models import SearchResult, Book, EB_base_url

#-------------------------------------------------------------------------------
def utf8_only(string_input):
    """Takes in string, removes non-utf chars, returns string.
    Doesn't do anything about punctuation."""

    try: # in case is Bool, etc
        try:
            decoded_str = string_input.decode('utf-8', errors='ignore')
            newstring_ascii = decoded_str.encode('utf-8', errors='ignore')
        except:
            encoded_str = string_input.encode('utf-8', errors='ignore')
            newstring_ascii= encoded_str.decode('utf-8', errors='ignore')

        if (len(newstring_ascii) >= 1 and newstring_ascii != " "):
            return newstring_ascii
        else:
            return None
    except:
        string_list=[]
        for char in list(string_input):
            try:
                new_char=char.decode('utf-8', errors='ignore')
                string_list.append(new_char)
            except:
                pass

        new_string = "".join(string_list)
        return new_string


#-------------------------------------------------------------------------------
def in_price_range(minprice = None, maxprice = None, price= None):
    """Takes in minimum and maximum price as well as item price,
    checks if item price is in price range.
    Converts to Integer to make sure cross comporable, b4 was rejecting Decimals.
    """
    in_range = True
    try:
        minprice = int(minprice)
    except:
        minprice = None
    try:
        maxprice = int(maxprice)
    except:
        maxprice = None
    try:
        price = int(price)
    except:
        price = None

    #For facsimile finder price may be None, but pass anyway.
    if (minprice or maxprice) and price:
        if minprice and maxprice and price not in range(minprice, maxprice+1):
            in_range = False
        elif minprice and price < minprice:
            in_range = False
        elif maxprice and price > maxprice:
            in_range = False

    return in_range


#-------------------------------------------------------------------------------
def remove_lower(query_string):
    """Takes in list of words, removes all words that don't start with caps,
    but only if length <= 4. Otherwise, it drops too many.
    Returns list.
    Meant to minimize garbage words included in search (und, and, de, y, etc)
    """
    #print "starting remove_lower with ",query_string
    word_list_upper = []

    for word in query_string.split():
        word = utf8_only(word)
        #print "word: ",word
        if word[0].isupper() or len(word) >= 4:
            # To make sure u' doesn't prevent intersection
            word_list_upper.append(str(word.upper()))

    query_upper = " ".join(word_list_upper)
    #print "returing ",query_upper
    return query_upper


#-------------------------------------------------------------------------------
def remove_punct(string_input):
    """Takes in string, removes punctuation, returns string sans punctuation.
    Note to self: I tried several methods, and w/ Lupo's propensity to have
    every kind of char and encoding available, using regex is the only one that
    consistently works.
    """
    #print "starting remove_punct with ",string_input
    punctless = re.sub(r'[^\w\s]',' ',string_input)
    # Get rid of excessive spaces
    new_string = re.sub(' +',' ', punctless)
    #print "returning ",new_string
    return new_string

#-------------------------------------------------------------------------------
def prep4url(string_input):
    """Takes in string, removes punctuation, turns spaces into %20, returns.
    Does nothing w/ umlauts.
    """
    #print "\nstarting prep4url with ",string_input
    noPunct = remove_punct(string_input)
    #print "noPunct ",noPunct
    new_string = noPunct.strip().replace(" ", "%20")
    #print "returning ",new_string,"\n"

    return new_string

#-------------------------------------------------------------------------------
def simplifyQueryString(trouble_query):
    """Sometimes sites like Facsimile Finder will reject a query
    if it has weird weird punctuation or umlauts or whatnot.
    This is a Plan B to give an easier string if that's a suspected cause of a fuckup.
    """
    print "about to simplify ",trouble_query
    acceptable = [
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
            "N", "O","P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
            "1","2","3","4","5","6","7","8","9","0"," ",
    ]
    cleaned = []
    for char in trouble_query:
        if char in acceptable:
            cleaned.append(char)

    cleaned_query = "".join(cleaned)
    print "cleaned to ",cleaned_query
    return cleaned_query

#-------------------------------------------------------------------------------
def convert_decimal(price):
    """Europeans would write two thousand euros as 2.000,00
    Americans do the opposite. This converts a Euro string to
    an American decimal for American django.
    """

    price = price.replace(".", "").strip()

    #If use , where Americans use ., replace with .
    # so 59,50 becomes 59.50
    if str(price)[-3] == ",":
        p1 = price[:-3]
        p2 = price[-2:]
        price = str(p1 + "." + p2)
    #below is to feed Decimal a real number sans the kind of , you get for 1,000
    price = price.replace(",", "").strip()
    price = Decimal(price)

    return price

#-------------------------------------------------------------------------------
def unparseEBlink(full_EB_link):
    """Get rid of all of EB's affiloiate bullshit to get real product link.
    Return real link.
    """
    try:
        parsed = urlparse.urlparse(full_EB_link)
        EBunparsed = urlparse.parse_qs(parsed.query)['url'][0]
        return EBunparsed
    except:
        return full_EB_link


#===============================================================================
class BookScraper(Scraper):

    def __init__(self, *args, **kwargs):
        self.site_choice = ""
        self.sr_dict = {}  #dict of SearchResult objs. k is identifying tuple.
        self.cumulative_errors = [] # list of q dicts
        self.current_qdict = None

    #---------------------------------------------------------------------------
    def make_searchresult(self, result_dict):
        """Takes an individual result dict, uses it to make SearchREsult obj
        Assuming no DB, so don't need to look for existing"""
        print "starting make_searchresult"
        from .utils import query_in_title

        this_result = None

        price = result_dict.get("price")
        price_currency = result_dict.get("price_currency")
        item_title = result_dict.get("item_title")
        query_string = result_dict.get("query_string")
        site_source = result_dict.get("site_source")
        seller = result_dict.get("seller")
        platform = result_dict.get("platform")#might be none
        original_url = result_dict.get("original_url") #might be real, might be a shit EB one.
        book = result_dict.get("book")
        img_url = result_dict.get("img_url")
        book_condition = result_dict.get("book_condition")

        id_tup = (item_title, seller, platform, site_source, price)
        print "Identifying info: ", id_tup

        if id_tup not in self.sr_dict.keys():
            print "New item"

            try:
            #if 2 == 2:
                this_result = SearchResult()
                this_result.found_by_query = query_string
                this_result.new_price = price
                this_result.new_price_currency = price_currency
                this_result.platform = platform
                this_result.book = book
                this_result.site_source = site_source
                this_result.seller = seller
                this_result.item_title = item_title
                this_result.original_url = original_url
                this_result.img_url = img_url
                this_result.book_condition = book_condition

                self.sr_dict[id_tup] = this_result
                this_result.show_data()
            except:
            #else:
                this_result = None


        else: #if obj exists
            print "EXISTS"
            this_result = self.sr_dict.get(id_tup)

            if query_string not in this_result.found_by_query.splitlines():
                this_result.update_found_by_query(query_string)

            #This is where I should add platform, if i consolodate them.

        if not this_result:
            print "no result to show; error"

        return this_result

    #---------------------------------------------------------------------------
    def bottomScrollWobble(self):
        """Used to coax EB into fetching more results.
        Goes to bottom of page slowly, then wobbles slightly higher, then down again.
        Written with assumption is being called from within a EB method,
        and will be used in a while loop that dictates when to stop.
        """
        print "starting bottomScrollWobble"

        #Go to bottom of page, scrolling slowly near bottom where trigger to get more results should be
        scrollInc = 1500
        while scrollInc > 0:
            scriptEx = "window.scrollTo(0, document.body.scrollHeight-%s);"%(str(scrollInc))
            self.selnium_browser.execute_script(scriptEx)
            sleep(0.1)
            scrollInc -= 100

        #scroll up slowly
        while scrollInc < 1500:
            scriptEx = "window.scrollTo(0, document.body.scrollHeight-%s);"%(str(scrollInc))
            self.selnium_browser.execute_script(scriptEx)
            sleep(0.1)
            scrollInc += 100

        #Scroll back down slowly
        while scrollInc > 0:
            scriptEx = "window.scrollTo(0, document.body.scrollHeight-%s);"%(str(scrollInc))
            self.selnium_browser.execute_script(scriptEx)
            sleep(0.1)
            scrollInc -= 100

        print "stop scrollwobble"

    #---------------------------------------------------------------------------
    def EBgetItemDiv(self):
        """Used to see if any items were found, to see if items found are same
        # as last time checked, and to get items for soup parsing.
        """

        found_items = []
        temp_content = self.selnium_browser.page_source
        tempsoup = bs4.BeautifulSoup(temp_content, "html.parser")

        h5 = tempsoup.findAll('h5')
        for div in tempsoup.findAll('div', {'id':'content_searchResults'} ):
            for rdiv in div: #"search results  before banner, etc"
                try:
                    found_items += rdiv.findAll('div', {'class':'result_details floatbox '} )
                    found_items += rdiv.findAll('div', {'class':'results_entry floatbox '} )
                except:
                    pass

        return found_items, h5


    #---------------------------------------------------------------------------
    def EB_done_searching(self):
        """I'm trying to wait until either I know there'e 0 results
        or it's done searching, but i think it stops too soon.
        """
        print "Making sure Eurobuch is done searching"

        timeout = time() + 30
        present = False
        noResults = False #This is True only if I find out there are no results. Used so I don't scroll wobble when I know there's nothing to find.
        while not present:
            if (time() < timeout):
                self.check4alert()#sometimes EB has stupid popups.
                print "waiting for EB to finish thinking"
                found_items, h5 = self.EBgetItemDiv()

                if len(h5) > 0 and ("Keine passenden Ergebnisse..." in h5[0].getText().strip() or "Keine aktuellen Ergebnisse..." in h5[0].getText().strip()) :
                    print "no results confirmed"
                    present = True
                    noResults = True
                    break
                elif len(found_items) > 0:
                    #print "found items: ",len(found_items)
                    present = True
                    break
                else:
                    temp_content = None
                    tempsoup = None
            elif time() > timeout:
                print "outta time2"
                break
            else:
                temp_content = None
                tempsoup = None


        ###########Sept 7 2017 those bastards trded out the next button for a forever scroll.
        #this section wobbles to the bottom of page and scrolls up a few times
        # triggering it to get more results and stopping when i keep finding the same results
        # 2 times in a row.
        if not noResults:
            print "Starting to scroll"
            scrolltime = 0
            sameResults = 0

            while True:

                preScrollItemNo, __ = self.EBgetItemDiv()
                print "Found items before scrolling: ",len(preScrollItemNo)

                self.bottomScrollWobble()
                sleep(2) # giving time to finish getting results
                scrolltime += 1

                postScrollItemNo, __ = self.EBgetItemDiv()
                print "Found items AFTER scrolling: ", len(postScrollItemNo)

                if len(preScrollItemNo) != len(postScrollItemNo):
                    sameResults = 0
                else:
                    sameResults += 1

                    print "Consecutive times results have been the same before and after scrolling : ",sameResults
                    print "Times I've checked: ",scrolltime
                    if sameResults >= 2 or scrolltime >= 5:
                        print "about to break"
                        break
            print "Done scrolling"
        else:
            print "no results, no reason to scroll"
        ###########end scrolling addition

        self.check4alert()#sometimes EB has stupid popups.
        self.content = self.selnium_browser.page_source

    #---------------------------------------------------------------------------
    def selnium_EB_custom(self, input_name, input_id, input_data, minprice, maxprice):
        """Takes full_url, dict of form id and onput k,v.
        returns site reading for Beautiful Soup, using selenium.
        """

        self.content = None
        attempts = 0

        base_url = "http://www.eurobuch.com/"
        self.full_url = base_url + "?sCountry=deu"
        wait_xpath1 = "//*[@id='search-main_title']"

        while not self.content and attempts < 10:

            attempts += 1
            #print "trying selenium EB Custom open, attempt ",attempts
            if not self.selnium_browser:
                self.prep_browser()
                print "got browser"

            try:
                self.selnium_browser.get(self.full_url)
                self.check4alert()
                print "got browser, checked for alert"
            except:
                print "browser exception, not sure what's up or if will work"
                pass
            print"about to wait x path"
            if wait_xpath1:
                try:
                    found = WebDriverWait(self.selnium_browser, 30).until(lambda browser : self.selnium_browser.find_element_by_xpath(wait_xpath1))
                    print"found x path"
                except:
                    if attempts < 5:
                        print "about to quit browser"
                        self.selnium_browser.close()
                        print "about to get browser"
                        self.prep_browser()
                        self.selnium_browser.get(self.full_url)
                        continue
                    else:
                        print "except, but attempts are >=5, gonna break."
                        break

            if input_name or input_id:
                if input_name:
                    inputElement = self.selnium_browser.find_element_by_name(input_name)
                elif input_id:
                    inputElement = self.selnium_browser.find_element_by_id(input_id)

                try:
                    inputElement.send_keys(input_data)
                except:
                    new_input = utf8_only(input_data)
                    try:
                        inputElement.send_keys(new_input)
                    except:
                        inputElement.send_keys(unicode(new_input))


            if minprice or maxprice:
                #maybe this is where it gets stuck on IE, IE sucks at xpath.

                #Sept 11 2017 this stopped working
                #ssbutt = self.selnium_browser.find_element_by_xpath("//*[@id='search-main']/div[5]/input[1]")
                #Velow woujld prob work bt i haven't tested, decided to try class instead
                #ssbutt = self.selnium_browser.find_element_by_xpath('//*[@id="search-main"]/div[2]/div[4]/input[1]')

                try:
                    ssbutt = self.selnium_browser.find_element_by_xpath('//*[@id="search-main"]/div[2]/div[4]/input[1]')
                except:
                    ssbutt = self.selnium_browser.find_element_by_xpath("//*[@id='search-main']/div[5]/input[1]")

                #that's actually the detailed search button.

                #print "found detailed search button" #just for troubleshooting when IE hangs.
                ssbutt.click()
                sleep(2)

                if minprice :
                    minelement = self.selnium_browser.find_element_by_id("search-main_minPrice")
                    try:
                        minelement.send_keys(minprice)
                    except:
                        minelement.send_keys(unicode(minprice))

                if maxprice:
                    maxelement = self.selnium_browser.find_element_by_id("search-main_maxPrice")
                    try:
                        maxelement.send_keys(maxprice)
                    except:
                        maxelement.send_keys(unicode(maxprice))

            #print "about to inputElement.submit"  #just for troubleshooting when IE hangs.
            print "about to submit"
            inputElement.submit()
            print "submitted"
            #print "submitted." #just for troubleshooting when IE hangs.

            self.EB_done_searching()
            self.check4alert()

        #print "returning content"
        return self.selnium_browser, self.content #broser,still open. res may be something or may be none


    #---------------------------------------------------------------------------
    def froek_soup(self, book, query_string, minprice, maxprice):
        print "froek_soup"
        results_dl = []
        base_dict = {
                "book":book, "site_source":"FuK", "seller":'Frölich und Kaufmann',
                "query_string":query_string
                }
        finished = False

        #some of this was running even if no results,
        #so now i check to make sure 1 seach is done and 2 there are results
        tries = 0
        restext = None
        while True:
            #get content again
            self.content = self.selnium_browser.page_source
            soup = bs4.BeautifulSoup(self.content, "html.parser")
            resdiv = soup.find("div", {"id": "sitFullsearchResult"})
            restext = resdiv.getText().strip()
            #print "restext ",restext
            if len(restext) > 0 or tries > 20:
                print "done thinking."
                break
            else:
                tries += 1
                sleep(1)
                print "try ",tries
        print "after while"

        if restext and "Keine Treffer" in restext:
            print "Keine Treffer"
            finished = True
        else:
            print "something found"
            for div in soup.findAll('div', {'class':'listDetails'} ):
                print "div in listdetails"
                for div2 in div.findAll('div', {'class':'titleBox'} ):
                    print "div2"
                    link_full = div2.findAll('a')#the title of the work is within this tag
                    original_url = link_full[0].get('href')
                    item_title = link_full[0].getText().strip()

                for div3 in div.findAll('div', {'class':'priceBox'} ):
                    price = div3.findAll('span', {'class':'price'} )
                    oldPrice = div3.findAll('span', {'class':'oldPrice'} )
                    priceNew = div3.findAll('span', {'class':'priceNew'} )

                    price_dict = {'price':price, 'oldPrice':oldPrice, 'priceNew':priceNew}

                    if len(priceNew) > 0:
                        pricediv = priceNew
                    elif len(price) > 0:
                        pricediv = price
                    else:
                        print "no price? error"

                    ugly_price = pricediv[0].getText()
                    pretty_price = ugly_price.strip()
                    #Sept 7 2017 site has all kinds of bullshit words before prices now.
                    # if "Jetzt nur: " in pretty_price:#for priceNew
                    #     temp = pretty_price.split("Jetzt nur: ")
                    #     price = temp[1]
                    # elif "nur " in pretty_price:#yet another thorn
                    #     temp = pretty_price.split("nur ")
                    #     price = temp[1]
                    # else:
                    #     price = pretty_price

                    #price_currency = price[-1]
                    #price = price[:-2]

                    #Sept 7 2017 change for bew bullshit words
                    pricelist = pretty_price.split()
                    price_currency = pricelist[-1]
                    price = pricelist[-2]
                    price = convert_decimal(price)

                    this_dict = base_dict.copy()

                    this_result = {
                            "item_title":item_title, "price":price,
                            "price_currency":price_currency,  "original_url":original_url
                            }

                    this_dict.update(this_result)
                    results_dl.append(this_dict)
                    #end with this item box

            for div in soup.findAll('div', {'id':'sitFullsearchResult'} ):
                print "looking for Next link"
                for div2 in div.findAll('div', {'id':'sitFullsearchNavigationTopArticles'} ):
                    resultbox_full = div2.findAll('h3')

                    #this doesn't appear to work.
                    for div3 in div2.findAll('div', {'class':'sitResultNavigation listRefine clear'} ):
                        for div4 in div3.findAll('div', {'class':'sitResultNavigationPages refineParams clear'} ):
                            for div5 in div4.findAll('div', {'id':'itemsPager'} ):
                                try:
                                    next_link=d.findAll('a', {'class':'next'} )
                                    print "next_link", next_link
                                    if len(next_link)<0:
                                        finished = True
                                except:
                                    print "no next or error"

        return results_dl, finished

    #---------------------------------------------------------------------------
    def get_froek_info(self, q_dict):
        """Custom webcrawl to get items link and prices from specific web site (http://www.froelichundkaufmann.de/Faksimile/).
        If the site changes the function will have to be retooled."""
        book = q_dict.get("book")
        these_results_total = []

        #query_string = book.title_de
        #Sept 7 2017: Noticed encoding was weird sometimes, could be reducing search results.
        query_string = book.title_de.encode('utf-8')

        minprice = q_dict.get("minprice")
        maxprice = q_dict.get("maxprice")

        try:
            print "Query ",query_string
        except:
            print "encoding error printing query"


        listify = remove_lower(query_string)
        searchify = ""
        for item in listify:
            searchify += item + "+"
        searchify_cut = searchify[:-1]
        #site_base = 'http://www.froelichundkaufmann.de/index.php?stoken=6536C2BF&force_sid=&lang=0&cl=search&searchparam='
        #self.full_url = site_base + searchify_cut
        #Sept 7 2017 noticed search was encoding strangely and searching for weird names, re did to send keys.
        site_base = "http://www.froelichundkaufmann.de/"
        self.full_url = site_base

        results = []
        js = None
        self.content = None
        search_xpath = "//*[@id='searchParam']"

        while True:
            #This below is important to prevent an invinite loop,
            #making t possible to look for only this site or use in long search of many sites.
            self.selnium_get_stay_open(js=None, wait_xpath=search_xpath, wait_name=None, continuing_browser=False)
            print "got selenium"

            try:
                WebDriverWait(self.selnium_browser, 5).until(lambda browser : self.selnium_browser.find_element_by_xpath(search_xpath))
                print "Page is ready!"
            except TimeoutException:
                print "Loading took too much time!"

            search_input = self.selnium_browser.find_element_by_xpath(search_xpath)
            safe_query = utf8_only(query_string)
            try:
                search_input.send_keys(safe_query)
            except:
                #doesn't break selenium but is wrong encoding
                #search_input.send_keys(unicode(safe_query.decode("iso-8859-4")))
                #breaks selenium
                #decoded_str = string_input.decode('utf-8', errors='ignore')
                #search_input.send_keys(decoded_str)
                try:
                    #WORKS!!!! correct coding, doesn't break!!!
                    #(edit: worksmost of the time)
                    search_input.send_keys(unicode(safe_query.decode("utf-8")))
                except:
                    #last resort
                    decoded_str = safe_query.decode('utf-8', errors='ignore').encode('iso-8859-4', errors='ignore')
                    search_input.send_keys(unicode(decoded_str.decode("iso-8859-4", errors='ignore')))

            print "sent query"
            search_input.send_keys(Keys.RETURN)
            try:
                found = WebDriverWait(self.selnium_browser, 20).until(lambda browser : self.selnium_browser.find_element_by_xpath("//*[@id='sitFullsearchResult']"))
                print "Page is ready!"
            except TimeoutException:
                print "Loading took too much time!"
            print "found?"

            if self.content:
                print "content"
                results_dl, finished = self.froek_soup(book, query_string, minprice, maxprice)
                results += results_dl#just to say how many in th end, doesn't get returned

                for results_dict in results_dl:
                    price = results_dict.get("price")
                    if in_price_range(minprice, maxprice, price):
                        this_result = self.make_searchresult(results_dict)
                        if not this_result:
                            self.cumulative_errors.append(results_dict)
                if finished:
                    print "finished, not looking for Next"
                    break
                else:
                    print "looking for Next"
                    try:
                        next_link = self.selnium_browser.find_element_by_class_name('next')
                        print "about to click"
                        next_link.click()
                        print "clicked"
                        self.selnium_get_stay_open(js=None, wait_xpath=wait_xpath, wait_name=None, continuing_browser=True)
                        print "got content. start over"
                    except:
                        print "except, about to break"
                        break

            else:
                error_dict = {
                        "book":q_dict.get("book"),
                        "site_source":'FuK',
                        query_string : q_dict.get("query_string")
                }

                self.cumulative_errors.append(error_dict)
                break

        print "done with FuK info"


    #---------------------------------------------------------------------------
    def fak_soup(self, book, query_string, minprice, maxprice):
        results_dl = []
        base_dict = {"book":book, "site_source":'DF', "seller":'das-faksimile',
                "query_string":query_string
                }

        soup = bs4.BeautifulSoup(self.content, "html.parser", from_encoding="UTF-8")
        for div in soup.findAll('div', {'class':'caption'} ):
            link_full = div.findAll('a')#the title of the work is within this tag
            original_url = link_full[0].get('href')
            item_title = link_full[0].getText()

            pricep = div.findAll('p', {'class':'price'} )
            price_new = div.findAll('span', {'class':'price-new'} )
            price_tax = div.findAll('span', {'class':'price-tax'} )

            if pricep:
                ugly_price = pricep[0].getText().strip().split()
                price = ugly_price[0]
            elif price_new:
                ugly_price = price_new[0].getText().strip().split()
                price = ugly_price[-1]
            else:
                ugly_price = price_tax[0].getText().strip().split()
                price = ugly_price[-1]

            price_currency = price[-1]
            price = price[:-1]
            price = convert_decimal(price)

            this_dict = base_dict.copy()
            this_result = {"item_title":item_title, "price":price,
                    "price_currency":price_currency, "original_url":original_url
                    }
            this_dict.update(this_result)
            results_dl.append(this_dict)

        print "done with fak soup, ", len(results_dl), " potential items"
        return results_dl

    #---------------------------------------------------------------------------
    def get_faksimile_info(self, q_dict):
        #self.current_qdict
        """Custom webcrawl to get items link and prices from specific web site
        (http://www.das-faksimile.com). If the site changes
        the function will have to be retooled.
        """

        book = q_dict.get("book")
        query_string = book.title_de
        try:
            print "Query ",query_string
        except:
            print "encoding error printing query"

        minprice = q_dict.get("minprice")
        maxprice = q_dict.get("maxprice")
        nolowers = remove_lower(query_string)
        searchify = prep4url(nolowers)

        site_base = 'http://das-faksimile.de/index.php?route=product/search&search='
        self.full_url = site_base + searchify
        errors = []

        self.get_site_info()
        if not self.content:
            print "no content, simplify search query"
            searchify = simplifyQueryString(nolowers)
            self.full_url = site_base + searchify

        if self.content:
            results_dl = self.fak_soup(book, query_string, minprice, maxprice)
            for results_dict in results_dl:
                price = results_dict.get("price")
                if in_price_range(minprice, maxprice, price):
                    this_result = self.make_searchresult(results_dict)
                    if not this_result:
                        self.cumulative_errors.append(results_dict)

        else:
            print "no content"
            error_dict = {
                    "book":q_dict.get("book"),
                    "site_source":"DF",
                    query_string : q_dict.get("query_string")
            }

            self.cumulative_errors.append(error_dict)

    #---------------------------------------------------------------------------
    def eurobuch_soup(self, base_url, book, query_string, minprice, maxprice, search_url):

        print "starting eb soup"
        #how on earth do I have the book? I don't feed it to the function
        finished = False
        new_results = []###EB is different from others, has 2 layers of results lists, bc of stupid offer box.
        soup = bs4.BeautifulSoup(self.content, "html.parser")

        #found_items=soup.findAll('div', {'id':'content_searchResults'} )
        # found_items=[]
        # for div in soup.findAll('div', {'id':'content_searchResults'} ):
        #     found_items+=div.findAll('div', {'class':'result_details floatbox '} )
        #     found_items+=div.findAll('div', {'class':'results_entry floatbox '} )
        #     found_items+=div.findAll('div', {'id':'results_list'} )
        #     found_items+=div.findAll('div', {'id':'seach_result_before_banner'} )
        #     found_items+=div.findAll('div', {'id':'seach_result_after_banner'} )
        #     found_items+=div.findAll('div', {'id':'seach_result_after_banner2'} )

            #i seem to be getting double items here, but I guess I'd rather double
            #and waste a few secs w/ an unnecesssary db trip than skip thigns.
        found_items = []
        for div in soup.findAll('div', {'id':'content_searchResults'} ):
            for rdiv in div: #"search results  before banner, etc"
                try:
                    found_items += rdiv.findAll('div', {'class':'result_details floatbox '} )
                    found_items += rdiv.findAll('div', {'class':'results_entry floatbox '} )
                except:
                    pass

        #print "found_items: (as in item divs, offer divs count as 1) ",len(found_items)
        if len(found_items) <= 0:
            finished = True
        else:
            found_urls = []
            offer_div = []
            for div2 in found_items: #div2 is something like info, info no imges, etc
                item_title = None
                price = None
                results_dl = []
                offer_div = [] #have to reset, otherwise I'm getting wrong price, offer div price is showing up in regular items

                titledata = div2.findAll('div', {'class':'res_aut_tit'} )
                if len(titledata) <= 0:
                    print "no title data"
                    #print "div2", div2
                else:
                    item_title = titledata[0].getText().strip()
                    #this info is the same for all offers in stupid box
                    for div3 in div2.findAll('div', {'class':'order_info'} ):

                        #order info is in all, but the bei is only in order info in the stupid box
                        div_all = div3.getText().strip()
                        div_lists = div_all.split()
                        try:
                            bei = div_lists.index(u'bei')
                            bei += 1
                            platform = div_lists[bei].strip()
                        except:
                            print " ERROR WITH BEI div lists"
                            print div_lists

                    for otherdiv in div2.findAll('div', {'class':'floatbox'} ):
                        offer_div = otherdiv.findAll('div', {'class':'offers'} ) #this is the annoying table box i didn't see until I was almsot done.

                    imglink = div2.find('img')['src']
                    if len(imglink) <= 0 or ("http" not in imglink): #when it was http: i was missing https: images
                        imglink = None

                    results_dict = {"img_url":imglink, "platform":platform, "book":book,
                            "site_source":'EB', "item_title":item_title,
                            "query_string":query_string,
                            "minprice":minprice, "maxprice":maxprice
                            }
                    #######divide up the variables that happen 1 way for a regular box, otherwise for stupid offer table
                    # variables that each has are: seller, europrice, link_full

                    if len(offer_div) <= 0:
                        #I do the singular stuff first so I can do the stuff that happens for all later, iterable for each.

                        seller_box=div2.findAll('div', {'style':'overflow: hidden; margin-bottom: 8px;'} )
                        if len(seller_box) > 0:
                            seller = seller_box[0].getText().strip()
                        else:
                            print "no seller, don't know what to do"

                        for div3 in div2.findAll('div', {'class':'order_info'} ):

                            europrice = div3.findAll('div', {'class':'europrice'} )
                            if len(europrice) <= 0:
                                europrice = div3.findAll('div', {'class':'price'} )

                            link_full = div3.findAll('a')

                        if link_full not in found_urls: #to reduce redundency. I'm not sure if it works.
                            var_dict = {"link_full":link_full,
                                    "europrice":europrice, "seller":seller
                                    }#just so i remember which are the temprary variables
                            indv_dict = results_dict.copy()
                            indv_dict.update(var_dict)
                            results_dl.append(indv_dict)
                            found_urls.append(link_full)
                        else:
                            print "in found_urls"

                    else:#for non offer div, normal shit.
                        for offer in offer_div:
                            print"\nOFFER! You might have to look all around the page and back for this one"
                            #seller_box=offer.find_all("td", attrs={'class':'td_center_middle'})
                            seller_row = offer.find_all("tr")
                            for tr in seller_row:
                                #using the same variable names as normal eb so i can use same formatting below.
                                seller_box = tr.find_all("span", attrs={'class':'merchant_name'})
                                if len(seller_box) > 0:
                                    seller = seller_box[0].getText().strip()
                                else:
                                    #this appear to never run
                                    print "alt seller box?"
                                    seller_box = tr.find_all("td")
                                    seller = seller_box[2].getText().strip()

                                europrice = tr.findAll('div', {'class':'europrice'} )
                                if len(europrice) <= 0:
                                    europrice = tr.findAll('div', {'class':'price'} )

                                link_full = tr.findAll('a')

                                if link_full not in found_urls: #to reduce redundency
                                    var_dict = {"link_full":link_full,
                                            "europrice":europrice,"seller":seller
                                            }#just so i remember which are the temprary variables
                                    indv_dict = results_dict.copy()
                                    indv_dict.update(var_dict)
                                    results_dl.append(indv_dict)
                                    found_urls.append(link_full)
                                else:
                                    print "in found_urls"

                #now in line w/ if found items:
                for rd in results_dl:
                    seller = rd.get("seller")
                    europrice = rd.get("europrice")
                    link_full = rd.get("link_full")

                    if "[Rating" in seller:
                        i = seller.split("[Rating")
                        temp = i[0]
                        temp2 = temp.split()
                        temp3 = temp2[:-3]#-1 would just get rid of rating, -2 would get rid of id number, -3 gets rid of country most of the time
                        temp4 = " ".join(temp3)
                        seller = temp4[:-1]#remove last comma

                    if "[Pos." in seller:
                        i = seller.split("[Pos.")
                        temp = i[0]
                        seller = temp

                    seller_list = seller.split()#get rid of stupid address.
                    for x in seller_list:
                        if len(x) >= 4 and x.isdigit():
                            i = seller_list.index(x)
                            seller_list = seller_list[:i]
                            seller = " ".join(seller_list)
                            seller = seller[:-1]#remove last comma

                    price_full = europrice[0].getText().strip()
                    pf1 = price_full.strip( ')' )
                    pf2 = pf1.strip( '(' )
                    price_list = pf2.split()
                    price_currency = price_list[-1]
                    price = price_list[-2]
                    price = convert_decimal(price)

                    try:
                        product_redirect=link_full[1].get('href') #item 0 was adding item to basket
                    except:
                        product_redirect=link_full[0].get('href') #item 0 was adding item to basket
                        #print "product_redirect",product_redirect

                    #original_url=base_url+product_redirect
                    original_url = unparseEBlink(product_redirect)

                    rd["seller"] = seller
                    rd["price"] = price
                    rd["price_currency"] = price_currency
                    rd["original_url"] = original_url
                    new_results.append(rd)

        return new_results, finished

    #---------------------------------------------------------------------------
    def get_eurobuch(self, q_dict):
        """Custom webcrawl to get items link and prices from specific web site
        (http://www.eurobuch.com/).
        If the site changes the function will have to be retooled.
        """

        self.full_url = EB_base_url+"/?sCountry=deu"

        #line of possible x paths I've tried
        #wait_xpath = "//*[@id='content_searchResults']/script"#nope
        #wait_xpath="//*[@id='seach_result_before_banner']"#nope
        #wait_xpath="//*[@id='results_engagementHint']"#nope
        #wait_xpath=["//*[@id='result_details_1']/div[1]/div[2]","//*[@id='searchHintsContainer']/div/div[2]"]
        #wait_xpath=["//*[@id='results_loader']"]
        #wait_xpath="//*[@id='col3_content']"#ends too soon, while still looking
        #wait_xpath2="//*[@id='searchHintsContainer']"#i think shows up whether are reuslts or not. Not good enough, sometimes abandons too early.
        #"//*[@id='content_history_loader']"#ends too soon
        #wait_xpath2="//*[@id='results_header']"#this makes next stop working, for some reason
        #wait_xpath2="//*[@id='content_history']"#ends toos soon
        #wait_xpath2="//*[@id='results_summary']"#looks like golden ticket but ends too soon sometimes
        #wait_xpath2="//*[@id='content_searchResults']"#doesn't wait for next, ends too soon.
        #wait_xpath2="//*[@id='seach_result_before_banner']"#doesn't wait for next, ends too soon.
        #wait_xpath=None
        #wait_xpath1="//*[@id='search-main_search']"#this is only on 1st page
        wait_xpath1 = "//*[@id='search-main_title']"#this is only on 1st page

        input_name = "search"
        input_id = "search-main_search"

        #this cuts down on bullshit searches. will it casue a problem when autor is in title?
        #but it bring me fewer results
        #input_name="title"
        #input_id="search-main_title"

        book = q_dict.get("book")
        query_string = q_dict.get("query_string")
        print "\nQuery: ", query_string
        minprice = q_dict.get("minprice")
        maxprice = q_dict.get("maxprice")
        input_data = query_string

        self.selnium_EB_custom(input_name=input_name, input_id=input_id, input_data=input_data, minprice=minprice, maxprice=maxprice)

        while True:
            tries = 0

            #self.content = None
            #Second time makking sure EB is searching, I think t is redundent after I made it scroll so many times.
            #self.EB_done_searching()
            #print "done with EB_done_searching in whie"

            if self.content:
                search_url = None
                results, finished = self.eurobuch_soup(EB_base_url, book,query_string, minprice, maxprice, search_url)
                for rd in results:
                    item_title = rd.get("item_title")
                    minprice = rd.get("minprice")
                    maxprice = rd.get("maxprice")
                    price = rd.get("price")

                    if len(item_title)>1 and in_price_range(minprice,maxprice,price):
                        this_result = self.make_searchresult(rd)
                        if not this_result:
                            print "not result"
                            self.cumulative_errors.append(rd)
                    else:
                        print "NOT ADDING"
                        try:
                            print item_title
                            print price
                        except:
                            pass

                tries += 1
                print "tries =", tries
                if finished:
                    break
                else:

                    #Sometimes I get the box that needs to be clicked here
                    #don't know if this works w/ this aler, haven't run it yet.
                    self.check4alert()

                    print "looking for next"
                    try:
                        print "about to xpath next"
                        if self.browserchoice != "IE":
                            self.selnium_browser.execute_script("window.stop();") #this causes a problem for IE
                            print "stoppedjs"
                        #sept 7 2017 THOSE SNEAKY FUCKING BASTARDS!
                        #no more next button, now must srcoll down.
                        next_link = self.selnium_browser.find_element_by_xpath("//img[contains(@src, 'button_table_next')]/parent::a")
                        print "found next link"
                        next_link.click()
                        print "clicked"
                    except NoSuchElementException:
                        print "no such element, no next"
                        break
                    except:
                        print "except, about to sleep"
                        sleep_int = randint(5,15)
                        print "exception looking for next, try again in ", str(sleep_int), " seconds?"
                        sleep(sleep_int)

            else:
                print "EB no content"
                error_dict = {
                        "book":q_dict.get("book"),
                        "site_source":"EB",
                        query_string : q_dict.get("query_string")
                }
                self.cumulative_errors.append(error_dict)
                break

        print "done with get_eurobuch"

    #---------------------------------------------------------------------------
    def merc_soup(self, query_string,book,minprice,maxprice,results):
        base_url = "http://www.mercurius-faksimile.de"
        soup = bs4.BeautifulSoup(self.content, "html.parser",from_encoding="utf-8")
        for div in soup.findAll('div', {'class':'article'} ):
            price_all = div.findAll('div', {'class':'price'})
            if len(price_all) > 0:
                price = price_all[0].getText()
                price_currency = price[0]
                price = Decimal(price[1:])
                #no need to convert decimal from this site

                for div2 in div.findAll('div', {'class':'content'} ):
                    link_full = div2.findAll('a') #the title of the work is within this tag
                    link = link_full[0].get('href')
                    original_url = base_url+link
                    item_title = link_full[0].getText()

                results_dict={"book":book, "site_source":'MF',
                        "item_title":item_title, "seller":"mercurius-faksimile",
                        "price":price, "price_currency":price_currency,
                        "original_url":original_url,"query_string":query_string
                        }

                if len(item_title) > 1 and in_price_range(minprice, maxprice, price):
                    this_result = self.make_searchresult(results_dict)
                    if not this_result:
                        self.cumulative_errors.append(results_dict)
        #Sept 6 2017 What is results and why do i pass it around? forgot.
        return list(results)


    #---------------------------------------------------------------------------
    def get_merc(self, q_dict):
        """Custom webcrawl to get items link and prices from specific web site
        (http://www.mercurius-faksimile.de/unser-programm-%C3%BCbersicht/).
        If the site changes the function will have to be retooled.
        """

        book = q_dict.get("book")
        query_string = book.title_de
        minprice = q_dict.get("minprice")
        maxprice = q_dict.get("maxprice")
        results = []
        errors = []
        query_string = query_string.strip().decode("utf-8")
        base_url = "http://www.mercurius-faksimile.de"
        self.full_url = base_url + "/unser-programm-%C3%BCbersicht/"
        #search_xpath  is also used later, don't get rid of it
        # Sept 5 2017, search xpath input changed from
        #search_xpath="//*[@id='modul_9340663_content']/div/form/div[1]/div[2]/input"
        #to
        search_xpath = "//*[@id='modul_25698683_content']/div/form/div[1]/div[2]/input"
        #wait_xpath=search_xpath #I used to think this made the conneciton refuse, but it doesn't seem to anymore

        #on Oct 6 2016
        #for a brief period div[4] x path didn't work, div[3] did, then div[4] worked again.
        #wait_xpath="//*[@id='page-1470104']/div[4]" #this is the results that shoild be returned.
        wait_xpath = "//*[@id='page-1470104']/div[3]"

        # Sept 5 2017, wait xpath input changed from
        #wait_xpath= "//*[@id='page-1470104']/div[3]"
        #to
        wait_xpath = "//*[@id='modul_25698683_content']/div/form/div[2]/input"
        #i don't remember if it used to be the OK button or not, but that's what it is now.

        # if browserchoice=="IE":
        #     wait_name="submit" #only need it for IE though
        #     search_xpath=None
        #     #Do I need to run JS for IE?
        # else:
        #     wait_name=None

        wait_name = None
        found = None
        print "about to selnium_get_stay_open"
        self.selnium_get_stay_open(js=None, wait_xpath=search_xpath, wait_name=wait_name, continuing_browser=False)
        print "got selenium"
        search_input = self.selnium_browser.find_element_by_xpath(search_xpath)
        search_input.send_keys(query_string)
        search_input.send_keys(Keys.RETURN)
        print "Sent keys and returned, did I get results?"

        #explanation for the following mess:
        #sometimes mer just does not respond to attempts to submit data, not even manually. don't know why.
        #usually closing the browser and starting over works, in this case. I don't know why.
        try:
        #if 2==2:
            found = None
            #the following is x path for results popup box.
            #on sept 5 2017 changed form
            #for x in ["//*[@id='page-1470104']/div[3]", "//*[@id='page-1470104']/div[4]"]:
            # to
            for x in ["//*[@id='page-2063175']/div[3]"]:
                try:
                    found = WebDriverWait(self.selnium_browser, 10).until(lambda browser : self.selnium_browser.find_element_by_xpath(x))
                    break
                except:
                    print "error, trying other."
                    found = None

            if not found:
                print "didn't work, gonna try other x path to find and send"
                try:
                    sub_but = self.selnium_browser.find_element_by_xpath("//*[@id='modul_9340663_content']/div/form/div[2]/input")
                except:
                    sub_but = self.selnium_browser.find_element_by_name(wait_name)
                    sub_but.click()
                    print "clicked"
                    sleep(3)#not trying wait x path, jsut waiting

        except:
        #else:
            #sometimes merc just sits there, won't let me subit, even manaully, for some reason.
            "error. gonne close browser and try again."
            self.selnium_browser.close()
            self.selnium_browser = None
            self.selnium_get_stay_open(js=None, wait_xpath=search_xpath, wait_name=wait_name, continuing_browser=False)
            search_input = self.selnium_browser.find_element_by_xpath(search_xpath)
            search_input.send_keys(query_string)

            #sub_but=self.selnium_browser.find_element_by_xpath("//*[@id='modul_9340663_content']/div/form/div[2]/input")
            sub_but = self.selnium_browser.find_element_by_xpath(wait_xpath)
            sub_but.click()
            try:
                search_input.send_keys(Keys.RETURN)
            except:
                pass

            sleep(5)#not trying wait x path, jsut waiting

        #end try/except mess for occasional merc unresponsiveness.
        if found:
            print "Found the results box"
            self.content = self.selnium_browser.page_source #Have to do this again with Chome, for some reason. Firefox doesn't need it but it doesn't hurt.
            results = self.merc_soup(query_string,book, minprice, maxprice, results)
        else:
            print "Result box not found"
            error_dict = {
                "book":q_dict.get("book"),
                "site_source":"MF",
                query_string : q_dict.get("query_string")
            }
            self.cumulative_errors.append(error_dict)

        try:#to get rid of the result box when done, and move on to other browser
            self.selnium_browser.find_element_by_link_text("zuklappen").click()
        except:
            pass
        try:
            inputElement = browser.find_element_by_xpath("//*[@id='page-1470104']/div[4]/div[2]/a").click()
        except:
            pass


    #---------------------------------------------------------------------------
    def finder_soup(self, book, query_string, minprice, maxprice):
        print "Facsimile Finder Soup"
        results_dl = []
        base_dict = {"book":book, "site_source":'FF', "seller":'Facsimile Finder',
                "query_string":query_string
                }

        soup = bs4.BeautifulSoup(self.content, "html.parser", from_encoding="UTF-8")
        for div in soup.findAll('div', {'class':'info_container'} ):
            item_title = div.find("h4").text.strip()
            print "\nitem title ",item_title
            try:
                sellersAll = div.find("p").text
            except:
                sellersAll = None
            print "sellers ",sellersAll
            links_all = div.findAll('a')#will return a lot, 1st is what we want
            original_url = links_all[0].get('href')
            print "original_url ",original_url

            this_dict = base_dict.copy()
            this_result = {"item_title":item_title, "original_url":original_url,
                    "seller": sellersAll
                    }

            pricediv = div.find('div', attrs={'class':'prices_container'})
            allps = pricediv.findAll('p')
            if len(allps)>2:
                #dont bother if only 2, then it's jusr out price and moe buying choices
                price_label = allps[0].getText().upper()
                book_condition = ""
                if "USED" in price_label:
                    book_condition += "U"
                if "NEW" in price_label:
                    book_condition += "N"

                #print "price_label: ",price_label
                price_value = allps[1].getText().strip()
                print "price_value: ",price_value
                price_currency = price_value[0]
                price = convert_decimal(price_value[2:])
                #print "price_currency  ",price_currency
                #print "price ",price
                this_result["price"] = price
                this_result["price_currency"] = price_currency
                this_result["book_condition"] = book_condition
            else:
                print "no price"
                #print allps
                #if just Our Price and More Buying Choices

            this_dict.update(this_result)
            results_dl.append(this_dict)

        print "done with finder soup, ", len(results_dl), " potential items"
        return results_dl


    #---------------------------------------------------------------------------
    def get_facfinder_info(self, q_dict):
        #self.current_qdict
        """Custom webcrawl to get items link and prices from specific web site
        (https://www.facsimilefinder.com/). If the site changes
        the function will have to be retooled.
        """
        print "starting get_facfinder_info"

        book = q_dict.get("book")
        query_string = book.title_de
        try:
            print "Query ",query_string
        except:
            print "encoding error printing query"

        minprice = q_dict.get("minprice")
        maxprice = q_dict.get("maxprice")
        nolowers = remove_lower(query_string)
        searchify = prep4url(nolowers)

        site_base = 'https://www.facsimilefinder.com/search/term/'
        self.full_url = site_base + searchify
        print "full_url ",self.full_url
        errors = []

        #note; Wed Nov 1 Mechanize treats 0 results as a 404 code, but then requests usually works
        self.get_site_info(url = self.full_url,  method_order_list = ["requests", "urllib2", "mechanize"])
        if not self.content:
            print "no content, simplify search query"
            searchify = simplifyQueryString(nolowers)
            self.full_url = site_base + searchify

        if self.content:
            results_dl = self.finder_soup(book, query_string, minprice, maxprice)
            for results_dict in results_dl:
                price = results_dict.get("price")
                if (not price) or in_price_range(minprice, maxprice, price):
                    this_result = self.make_searchresult(results_dict)
                    if not this_result:
                        self.cumulative_errors.append(results_dict)

        else:
            print "no content"
            error_dict = {
                "book":q_dict.get("book"),
                "site_source":"FF",
                query_string : q_dict.get("query_string")
            }
            self.cumulative_errors.append(error_dict)
