Mangafox Download Script
========================

About
-----
Mangafox Download Script is a manga downloader similar to my old Onemanga Download Script (although onemanga.com shut down). It works by scraping the image URL from every page in a manga chapter. It then it downloads all the images.
I created this because I prefer reading manga with the use of a viewer like Comix. I also prefer keeping manga on my hard drive in case I am not connected to the internet.

Dependencies
------------

  * Python 3.3 or better
  * BeautifulSoup (``pip install beautifulsoup4``)

Tested on Arch Linux. It should work on any Linux, OS X, or Windows machine as long as the dependencies are installed.

Usage
-----

Mandatory argument:
  -m --manga <Manga Name>

 Optional Argumentsq:
   -s <Start At Chapter>
   -e <End At Chapter>
   -c Create cbz Archive
   -r Remove image files after the creation of cbz archive"""

To download an entire series:

    ~ $ python mfdl.py -m MANGA_NAME

To download a specific chapter:

    ~ $ python mfdl.py -m MANGA_NAME -s CHAPTER

To download a range of manga chapter:

    ~ $ python mfdl.py python mfdl.py -m MANGA_NAME -s CHAPTER_START -e CHAPTER_END

Examples
--------
Download all of The World God Only Knows:

    ~ $ python mfdl.py -m "The World God Only Knows"

Download The World God Only Knows chapter 222.5:

    ~ $ python mfdl.py -m "The World God Only Knows" -s 222.5

Download The World God Only Knows chapters 190-205:

    ~ $ python mfdl.py -m "The World God Only Knows" -s 190 -e 205

Notes
-----
Please do not overuse and abuse this and destroy Mangafox. If you've got some cash, why not donate some to them and help them keep alive and combat server costs? I really would not like people to destroy Mangafox because of greedy downloading. Use this wisely and don't be evil.
