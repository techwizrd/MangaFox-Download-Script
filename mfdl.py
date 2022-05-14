#!/usr/bin/env python
# encoding: utf-8

import sys
import argparse
import os
import urllib.request
import glob
import shutil
import re
import time
from itertools import filterfalse
from zipfile import ZipFile
from functools import reduce
from bs4 import BeautifulSoup
from contextlib import closing
from collections import OrderedDict

from io import StringIO
import gzip

URL_BASE = "https://m.fanfox.net/"


def debug_http_requests():
    http_handler = urllib.request.HTTPHandler(debuglevel = 1)
    https_handler = urllib.request.HTTPSHandler(debuglevel = 1)
    opener = urllib.request.build_opener(http_handler, https_handler)
    urllib.request.install_opener(opener)

def get_page_content(url):
    """Download a page and return a BeautifulSoup object of the html"""
    if url[0:2] == '//':
        # Absolute URL with no protocol
        url = 'https:' + url
    elif url[0] == '/':
        # Relative URL
        url = URL_BASE + url

    request = urllib.request.Request(url)
    request.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36")
    request.add_header("Cookie", "isAdult=1")
    request.add_header("Referer", URL_BASE)
    response = urllib.request.urlopen(request)

    if response.info().get('Content-Encoding') == 'gzip':
        gzipFile = gzip.GzipFile(fileobj=response)
        page_content = gzipFile.read()
    else:
        page_content = response.read()

    return page_content

def get_page_soup(url):
    print('Parsing page: ' + url)
    page_content = get_page_content(url)
    soup_page = BeautifulSoup(page_content, "html.parser")

    return soup_page

def get_chapter_urls(manga_name):
    """Get the chapter list for a manga"""
    replace = lambda s, k: s.replace(k, '_')
    manga_url = reduce(replace, [' ', '-'], manga_name.lower())
    url = '{0}manga/{1}/'.format(URL_BASE, manga_url)
    print('Url: ' + url)
    soup = get_page_soup(url)
    
    # If the title does not exist, a search page will be returned
    manga_does_not_exist = soup.find('form', {'name': 'searchform'})
    if manga_does_not_exist:
        search_sort_options = 'sort=views&order=za'
        url = '{0}/search.php?name={1}&{2}'.format(URL_BASE,
                                                   manga_url,
                                                   search_sort_options)
        soup = get_page_soup(url)
        results = soup.find_all('a', {'class': 'series_preview'})
        error_text = 'Error: Manga \'{0}\' does not exist'.format(manga_name)
        error_text += '\nDid you meant one of the following?\n  * '
        error_text += '\n  * '.join([manga.text for manga in results][:10])
        sys.exit(error_text)

    # Check if this manga has been licensed
    warning = soup.find('div', {'class': 'warning'})
    if warning and 'licensed' in warning.text:
        sys.exit('Error: ' + warning.text)

    # Get chapter list
    # Chapter links will have the form /vNN/cNNN/1.html
    # or /cNNN/1.html
    links = soup.find_all('a', href = re.compile('/{0}/(.*/)?c\d+/.*\.html'.format(manga_url)))
    if(len(links) == 0):
        sys.exit('Error: Manga either does not exist or has no chapters')

    chapters = OrderedDict()
    for link in links:
        # Ignore the "Read Now" button
        if link.get('class'):
            continue
        chapter_id = get_chapter_number(link['href'])
        if chapter_id == None:
            continue
        chapters[float(chapter_id)] = link['href']

    if len(chapters) == 0:
        sys.exit('Error: Manga has no chapters')

    ordered_chapters = OrderedDict(sorted(chapters.items()))

    return ordered_chapters

def get_page_numbers(soup):
    """Return the list of page numbers from the parsed page"""
    page_select = soup.find('select', {'class': 'mangaread-page'})
    pages = page_select.find_all('option')
    page_max = 1
    for page in pages:
        page_max = max(page_max, int(page.text))

    return range(1, page_max)

def get_chapter_image_urls(url_fragment):
    """Find all image urls of a chapter and return them"""
    chapter_number = get_chapter_number(url_fragment)
    print('Getting page urls for chapter {0}'.format(chapter_number))

    chapter = get_page_soup(url_fragment)
    pages = get_page_numbers(chapter)

    chapter_url = os.path.dirname(url_fragment) + '/'
    image_urls = []
    print('Getting {0} image urls for chapter {1}...'.format(len(pages), chapter_number))
    for page in pages:
        page_url = '{0}{1}.html'.format(chapter_url, page)
        print('page: {0}'.format(page))
        print('Getting image url from {0}'.format(page_url))
        page_soup = get_page_soup(page_url)
        image_div = page_soup.find('div', id='viewer')
        if image_div == None:
            continue
        images = image_div.find_all('img')
        if images: image_urls.append(images[0]['src'])
    return image_urls

def get_chapter_number(url_fragment):
    """Parse the url fragment and return the chapter number."""
    re_chapter = re.compile('/c\d+/')
    chapter_match = re_chapter.search(url_fragment)
    if chapter_match == None:
        return None
    return chapter_match.group()[2:-1]

def download_urls(image_urls, manga_name, chapter_number):
    """Download all images from a list"""
    download_dir = '{0}/{1}/'.format(manga_name, chapter_number)
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir)
    for i, url in enumerate(image_urls):
        filename = './{0}/{1}/{2:03}.jpg'.format(manga_name, chapter_number, i)

        print('Downloading {0} to {1}'.format(url, filename))
        try:
            data = get_page_content(url)
        except urllib.error.HTTPError as http_err:
            print('HTTP error: {0} {1}'.format(http_err.code, http_err.reason))
            if http_err.code == 404:
                # Skip this page
                continue

        with open(filename, 'b+w') as f:
            f.write(data)

        time.sleep(2)

def make_cbz(dirname):
    """Create CBZ files for all JPEG image files in a directory."""
    zipname = dirname + '.cbz'
    images = sorted(glob.glob(os.path.abspath(dirname) + '/*.jpg'))
    with closing(ZipFile(zipname, 'w')) as zipfile:
        for filename in images:
            print('writing {0} to {1}'.format(filename, zipname))
            zipfile.write(filename)

def download_manga(manga_name, range_start=1, range_end=None, b_make_cbz=False, remove=False):
    """Download a range of a chapters"""

    chapter_urls = get_chapter_urls(manga_name)

    if range_end == None : range_end = max(chapter_urls.keys())

    for chapter, url in filterfalse (lambda chapter_url:
                                     chapter_url[0] < range_start
                                     or chapter_url[0] > range_end,
                                     chapter_urls.items()):
        chapter_number = get_chapter_number(url)
        if chapter_number == None:
            continue

        print('===============================================')
        print('Chapter ' + chapter_number)
        print('===============================================')
        image_urls = get_chapter_image_urls(url)
        download_urls(image_urls, manga_name, chapter_number)
        download_dir = './{0}/{1}'.format(manga_name, chapter_number)
        if b_make_cbz is True:
            make_cbz(download_dir)
            if remove is True: shutil.rmtree(download_dir)

def main():
    parser = argparse.ArgumentParser(description='Manga Fox Downloader')

    parser.add_argument('--manga', '-m',
                        required=True,
                        action='store',
                        help='Manga to download')

    parser.add_argument('--start', '-s',
                        action='store',
                        type=int,
                        default=1,
                        help='Chapter to start downloading from')

    parser.add_argument('--end', '-e',
                        action='store',
                        type=int,
                        default=None,
                        help='Chapter to end downloading to')

    parser.add_argument('--cbz', '-c',
                        action="store_true",
                        default=False,
                        help="Create cbz archive after download")

    parser.add_argument('--remove', '-r',
                        action="store_true",
                        default=False,
                        help="Remove image files after the creation of a cbz archive")

    parser.add_argument('--debug', '-d',
                        action="store_true",
                        default=False,
                        help="Enable HTTP request debug logging")

    args = parser.parse_args()

    print('Getting chapter of ', args.manga, 'from ', args.start, ' to ', args.end)

    if args.debug:
        debug_http_requests()

    download_manga(args.manga, args.start, args.end, args.cbz, args.remove)

if __name__ == "__main__":
    main()
