#!/usr/bin/python

'''Mangafox Download Script by Kunal Sarkhel <theninja@bluedevs.net>'''

import sys
import os
import urllib
from BeautifulSoup import BeautifulSoup
#from IPython.Shell import IPShellEmbed #for debug purposes

URL_BASE = "http://mangafox.com/"
#ipshell = IPShellEmbed()

def get_page_soup(url):
    """Download a page and return a BeautifulSoup object of the html"""
    urllib.urlretrieve(url, "page.html")
    html = ""
    with open("page.html") as html_file:
        for line in html_file:
            html += line
    return BeautifulSoup(html)


def get_chapter_urls(manga_name):
    """Get the chapter list for a manga"""
    url = "{0}manga/{1}?no_warning=1".format(URL_BASE, manga_name.lower())
    soup = get_page_soup(url)
    chapters = []
    links = soup.findAll('a', {"class": "chico"})
    for link in links:
        chapters.append(link['href'])
    return list(set(chapters)) # ugly yo-yo code to remove duplicates


def get_page_numbers(soup):
    """Return the list of page numbers from the parsed page"""
    raw = soup.findAll('select', {'class': 'middle'})[0]
    raw_options = raw.findAll('option')
    pages = []
    for html in raw_options:
        pages.append(html['value'])
    return pages


def get_chapter_image_urls(url_fragment):
    """Find all image urls of a chapter and return them"""
    print "Getting chapter urls"
    chapter_url = URL_BASE + url_fragment
    chapter = get_page_soup(chapter_url)
    pages = get_page_numbers(chapter)
    image_urls = []
    print "Getting image urls..."
    for page in pages:
        print "Getting image url from {0}{1}.html".format(url_fragment, page)
        page_soup = get_page_soup(chapter_url + page + ".html")
        images = page_soup.findAll('img', {'id': 'image'})
        image_urls.append(images[0]['src'])
    return image_urls


def get_chapter_number(url_fragment):
    """Parse the url fragment and return the chapter number."""
    return ''.join(url_fragment.rsplit("/")[3:-1])


def download_urls(image_urls, manga_name, chapter_number):
    """Download all images from a list"""
    num = 1
    os.makedirs("{0}/{1}/".format(manga_name, chapter_number))
    for url in image_urls:
        filename = "./{0}/{1}/{2:03}.jpg".format(manga_name,
                                                 chapter_number,
                                                 num)
        print "Downloading {0} to {1}".format(url, filename)
        urllib.urlretrieve(url, filename)
        num = num + 1


def download_manga_range(manga_name, range_start, range_end):
    """Download a range of a chapters"""
    print "Getting chapter urls"
    chapter_urls = get_chapter_urls(manga_name)
    chapter_urls.sort()
    for url_fragment in chapter_urls[int(range_start)-1:int(range_end)+1]:
        chapter_number = get_chapter_number(url_fragment)
        print("===============================================")
        print("Chapter " + chapter_number)
        print("===============================================")
        #image_urls = get_chapter_image_urls(url_fragment)
    os.remove("page.html")


def download_manga(manga_name, chapter_number=None):
    """Download all chapters of a manga"""
    chapter_urls = get_chapter_urls(manga_name)
    chapter_urls.sort()
    if chapter_number:
        url_fragment = chapter_urls[int(chapter_number)-1]
        chapter_number = get_chapter_number(url_fragment)
        print("===============================================")
        print("Chapter " + chapter_number)
        print("===============================================")
        image_urls = get_chapter_image_urls(url_fragment)
        download_urls(image_urls, manga_name, chapter_number)
    else:
        for url_fragment in chapter_urls:
            chapter_number = get_chapter_number(url_fragment)
            print chapter_number
            print("===============================================")
            print("Chapter " + chapter_number)
            print("===============================================")
            image_urls = get_chapter_image_urls(url_fragment)
            download_urls(image_urls, manga_name, chapter_number)
    os.remove("page.html")

if __name__ == '__main__':
    if len(sys.argv) == 4:
        download_manga_range(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3:
        download_manga(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        download_manga(sys.argv[1])
    else:
        print("USAGE: mfdl.py [MANGA_NAME]")
        print("       mfdl.py [MANGA_NAME] [CHAPTER_NUMBER]")
        print("       mfdl.py [MANGA_NAME] [RANGE_START] [RANGE_END]")
