mfdl
====

About
-----
mfdl (mangafox download script) is a mangafox scraper. It uses BeautifulSoup,
re, zipfile and zlib. It should work on basically any Unix-like, not guaranteed
on Windows. Might not work if you're using a case-insensitive file system.

Usage
-----
To download an entire series:

    $ python mfdl.py [MANGA_NAME]

To download a specific chapter:

    $ python mfdl.py [MANGA_NAME] [CHAPTER_NUMBER]

To download a range of manga chapter:

    $ python mfdl.py [MANGA_NAME] [RANGE_START] [RANGE_END]

Notes
-----
Please do not overuse and abuse this and destroy Mangafox. If you've got some
cash, why not donate some to them and help them keep alive and combat server
costs? I really would not like people to destroy Mangafox because of greedy
downloading. Use this wisely and don't be evil.

## This is a fork from [techwizrd/MangaFox-Download-Script](https://github.com/techwizrd/MangaFox-Download-Scrip).
Since the original author apparently didn't care enough about it, I also merged
work from [siikamiika/MangaFox-Download-Script](https://github.com/siikamiika/MangaFox-Download-Script).

