#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Mangafox Download Script by Kunal Sarkhel <theninja@bluedevs.net>"""

#from IPython.Shell import IPShellEmbed #for debug purposes
#ipshell = IPShellEmbed()

import sys
import os
import urllib
import glob
import shutil
from zipfile import ZipFile
from contextlib import closing
from itertools import izip, count

from BeautifulSoup import BeautifulSoup

URL_BASE = 'http://mangafox.com/'

def get_page_soup(url):
    """Download a page and return a BeautifulSoup object of the html"""
    with closing(urllib.urlopen(url)) as html_file:
        return BeautifulSoup(html_file.read())

def get_chapter_urls(manga_name):
    """Get the chapter list for a manga"""
    url = '{0}manga/{1}?no_warning=1'.format(URL_BASE, manga_name.lower())
    print 'URL: ', url
    soup = get_page_soup(url)
    chapters = []
    links = soup.findAll('a', {'class': 'ch'})
    for link in links:
        chapters.append(link['href'])
    if not links:
        print 'Warning: Manga either unable to be found, or no chapters - please check the url above'
    # ugly yo-yo code to remove duplicates
    return list(set(chapters))

def get_page_numbers(soup):
    """Return the list of page numbers from the parsed page"""
    raw = soup.findAll('select', {'class': 'middle'})[0]
    raw_options = raw.findAll('option')
    return (html['value'] for html in raw_options)

def get_chapter_image_urls(url_fragment):
    """Find all image urls of a chapter and return them"""
    print 'Getting chapter urls'
    url_fragment = os.path.dirname(url_fragment) + '/'
    chapter_url = URL_BASE + url_fragment
    chapter = get_page_soup(chapter_url)
    pages = get_page_numbers(chapter)
    image_urls = []
    print 'Getting image urls...'
    for page in pages:
        print 'url_fragment: ', url_fragment
        print 'page: ', page
        print 'Getting image url from {0}{1}.html'.format(url_fragment, page)
        page_soup = get_page_soup(chapter_url + page + '.html')
        images = page_soup.findAll('img', {'id': 'image'})
        image_urls.append(images[0]['src'])
    return image_urls

def get_chapter_number(url_fragment):
    """Parse the url fragment and return the chapter number."""
    return ''.join(url_fragment.rsplit('/')[3:-1])

def download_urls(image_urls, manga_name, chapter_number):
    """Download all images from a list"""
    os.makedirs('{0}/{1}/'.format(manga_name, chapter_number))
    for url, num in izip(image_urls, count(1)):
        filename = './{0}/{1}/{2:03}.jpg'.format(manga_name,
            chapter_number, num)
        print 'Downloading {0} to {1}'.format(url, filename)
        urllib.urlretrieve(url, filename)

def make_cbz(dirname):
    """Create CBZ files for JPEG image files in a directory."""
    dirname = os.path.abspath(dirname)
    zipname = dirname + '.cbz'
    images = glob.glob(dirname + '/*.jpg')
    with closing(ZipFile(zipname, 'w')) as zipfile:
        for filename in images:
            print 'writing {0} to {1}'.format(filename, zipname)
            zipfile.write(filename)

def download_manga_range(manga_name, range_start, range_end):
    """Download a range of a chapters"""
    print 'Getting chapter urls'
    chapter_urls = get_chapter_urls(manga_name)
    chapter_urls.sort()
    for url_fragment in chapter_urls[int(range_start)-1:int(range_end)+1]:
        chapter_number = get_chapter_number(url_fragment)
        print '=' * 48
        print 'Chapter ', chapter_number
        print '=' * 48
        image_urls = get_chapter_image_urls(url_fragment)
        download_urls(image_urls, manga_name, chapter_number)
        download_dir = './{0}/{1}'.format(manga_name, chapter_number)
        make_cbz(download_dir)
        shutil.rmtree(download_dir)

def download_manga(manga_name, chapter_number=None):
    """Download all chapters of a manga"""
    chapter_urls = get_chapter_urls(manga_name)
    chapter_urls.sort()
    if chapter_number is not None:
        url_fragment = chapter_urls[int(chapter_number)-1]
        chapter_number = get_chapter_number(url_fragment)
        print '=' * 48
        print 'Chapter ', chapter_number
        print '=' * 48
        image_urls = get_chapter_image_urls(url_fragment)
        download_urls(image_urls, manga_name, chapter_number)
        download_dir = './{0}/{1}'.format(manga_name, chapter_number)
        make_cbz(download_dir)
        shutil.rmtree(download_dir)
    else:
        for url_fragment in chapter_urls:
            chapter_number = get_chapter_number(url_fragment)
            print '=' * 48
            print 'Chapter ', chapter_number
            print '=' * 48
            image_urls = get_chapter_image_urls(url_fragment)
            download_urls(image_urls, manga_name, chapter_number)
            download_dir = './{0}/{1}'.format(manga_name, chapter_number)
            make_cbz(download_dir)
            shutil.rmtree(download_dir)

if __name__ == '__main__':
    if len(sys.argv) == 4:
        download_manga_range(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3:
        download_manga(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        download_manga(sys.argv[1])
    else:
        print('USAGE: mfdl.py [MANGA_NAME]')
        print('       mfdl.py [MANGA_NAME] [CHAPTER_NUMBER]')
        print('       mfdl.py [MANGA_NAME] [RANGE_START] [RANGE_END]')
