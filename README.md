Mangafox Download Script
========================

about
-----
Mangafox Download Script is a manga downloader similar to my old Onemanga Download Script (although onemanga.com shut down). It works by downloading each individual page and parsing it for the image url. Then it downloads all the images.
I created this because I prefer reading manga with the use of a viewer like Comix. I also prefer keeping manga on my hard drive in case I am not connected to the internet.

dependencies
------------
Python 2.6 and up (not tested with Python 3)
BeautifulSoup (pip install beautifulsoup)

Tested on Ubuntu Linux 9.04, 9.10, 10.04, and 10.10. It should work on any Linux, OS X, or Windows machine as long as they've got the dependencies.

usage
-----
to download an entire series
    ~ $ python mfdl.py [MANGA_NAME]
to download a specific chapter (downloads wrong chapter if a manga has a strange numbering scheme like starting with 0)
    ~ $ python mfdl.py [MANGA_NAME] [CHAPTER_NUMBER]
to download a range of manga chapter (same caveats as above)
    ~ $ python mfdl.py [MANGA_NAME] [RANGE_START] [RANGE_END]

examples
--------
download all of Yureka
    ~ $ python mfdl.py Yureka
download Yureka chapter 165
    ~ $ python mfdl.py Yureka 165
download Yureka chapters 160-170
    ~ $ python mfdl.py Yureka 160 170

notes
-----
Please do not overuse this and destroy Mangafox. If you've got some cash, why not donate some to them and help them keep alive and combat server costs? I really would not like people to destroy Mangafox because of greedy downloading. Use this wisely and don't be evil.
