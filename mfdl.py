#!/usr/bin/env python3

import argparse
import gzip
import os
import random
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from collections.abc import Iterable
from contextlib import closing
from functools import reduce
from itertools import filterfalse
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from bs4 import BeautifulSoup
from tqdm import tqdm

URL_BASE = "https://m.fanfox.net/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": URL_BASE,
}


def debug_http_requests() -> None:
    http_handler = urllib.request.HTTPHandler(debuglevel=1)
    https_handler = urllib.request.HTTPSHandler(debuglevel=1)
    opener = urllib.request.build_opener(http_handler, https_handler)
    urllib.request.install_opener(opener)


def normalize_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"{URL_BASE.rstrip('/')}{url}"
    return url


def request_url(url: str) -> urllib.request.Request:
    return urllib.request.Request(normalize_url(url), headers=DEFAULT_HEADERS)


def read_response_content(response: Any) -> bytes:
    payload = response.read()
    encoding = response.info().get("Content-Encoding", "")

    if encoding == "gzip":
        return gzip.decompress(payload)

    if payload.startswith(b"\x1f\x8b"):
        return gzip.decompress(payload)

    return payload


def get_page_content(url: str) -> tuple[int, str, bytes]:
    with closing(urllib.request.urlopen(request_url(url))) as response:
        status = response.getcode()
        content_type = response.headers.get_content_type()
        payload = read_response_content(response)
        return status, content_type, payload


def get_page_soup(url: str) -> BeautifulSoup:
    print(f"Parsing page: {url}")
    _, _, page_content = get_page_content(url)
    return BeautifulSoup(page_content, "html.parser")


def manga_to_slug(manga_name: str) -> str:
    def replacer(value: str, key: str) -> str:
        return value.replace(key, "_")

    return reduce(replacer, [" ", "-"], manga_name.lower())


def get_chapter_urls(manga_name: str) -> OrderedDict[float, str]:
    manga_slug = manga_to_slug(manga_name)
    url = f"{URL_BASE}manga/{manga_slug}/"
    print(f"URL: {url}")

    soup = get_page_soup(url)
    manga_does_not_exist = soup.find("form", {"name": "searchform"})
    if manga_does_not_exist:
        search_sort_options = "sort=views&order=za"
        search_url = f"{URL_BASE}search?name={manga_slug}&{search_sort_options}"
        soup = get_page_soup(search_url)
        results = soup.find_all("a", {"class": "series_preview"})
        error_text = f"Error: Manga '{manga_name}' does not exist"
        error_text += "\nDid you mean one of the following?\n  * "
        error_text += "\n  * ".join([manga.text for manga in results][:10])
        raise SystemExit(error_text)

    warning = soup.find("div", {"class": "warning"})
    if warning and warning.text and "licensed" in warning.text.lower():
        raise SystemExit(f"Error: {warning.text}")

    links = soup.find_all("a", href=re.compile(rf"/{manga_slug}/(.*/)?c\d+/.*\.html"))
    if not links:
        raise SystemExit("Error: Manga either does not exist or has no chapters")

    chapters: OrderedDict[float, str] = OrderedDict()
    for link in links:
        if link.get("class"):
            continue
        href = link.get("href")
        if not isinstance(href, str):
            continue
        chapter_id = get_chapter_number(href)
        if chapter_id is None:
            continue
        chapters[chapter_id] = href

    if not chapters:
        raise SystemExit("Error: Manga has no chapters")

    return OrderedDict(sorted(chapters.items()))


def get_page_numbers(soup: BeautifulSoup) -> list[int]:
    page_select = soup.find("select", {"class": "mangaread-page"})
    if page_select:
        return [
            int(option.text) for option in page_select.find_all("option") if option.text.isdigit()
        ]

    old_page_select = soup.find("select", {"class": "m"})
    if old_page_select:
        page_numbers: list[int] = []
        for option in old_page_select.find_all("option"):
            value = option.get("value")
            if isinstance(value, str) and value.isdigit():
                page_numbers.append(int(value))
        return page_numbers

    raise SystemExit("Error: Unable to determine page list")


def get_chapter_image_urls(url_fragment: str) -> list[str]:
    chapter_number = get_chapter_number(url_fragment)
    if chapter_number is None:
        raise SystemExit(f"Error: invalid chapter URL fragment: {url_fragment}")

    print(f"Getting page URLs for chapter {chapter_number:g}")
    chapter_soup = get_page_soup(url_fragment)
    pages = get_page_numbers(chapter_soup)

    chapter_base_url = os.path.dirname(url_fragment.rstrip("/")) + "/"
    image_urls: list[str] = []
    print(f"Getting {len(pages)} image URLs...")
    for page in pages:
        page_url = f"{chapter_base_url}{page}.html"
        print(f"Getting image URL from {page_url}")
        page_soup = get_page_soup(page_url)
        viewer_div = page_soup.find("div", id="viewer")
        image = None
        if viewer_div:
            image = viewer_div.find("img")
        if image is None:
            image = page_soup.find("img", {"id": "image"})

        if image and image.get("src"):
            src = image.get("src")
            if isinstance(src, str):
                image_urls.append(src)
            else:
                print(f"Warning: invalid image src for page {page_url}")
        else:
            print(f"Warning: image not found for page {page_url}")

    return image_urls


def get_chapter_number(url_fragment: str) -> float | None:
    match = re.search(r"/c(\d+(?:\.\d+)?)/", url_fragment)
    if match is None:
        return None
    return float(match.group(1))


def write_binary_file(filename: Path, data: bytes) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_bytes(data)


def download_urls(
    image_urls: Iterable[str],
    manga_name: str,
    chapter_number: float,
    avg_delay: float = 2.0,
    max_retries: int = 5,
) -> None:
    image_list = list(image_urls)
    chapter_label = f"{chapter_number:g}"
    download_dir = Path(manga_name) / chapter_label
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True)

    random.seed()
    progress = tqdm(
        image_list,
        desc=f"Chapter {chapter_label}",
        unit="img",
        disable=not sys.stderr.isatty(),
    )
    for index, url in enumerate(progress):
        filename = download_dir / f"{index:03}.jpg"

        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                status, content_type, data = get_page_content(url)
                if status < 200 or status >= 300:
                    print(
                        f"Warning: got status {status} for {url} (attempt {attempt}/{max_retries})"
                    )
                elif not content_type.startswith("image/"):
                    print(
                        f"Warning: expected image for {url}, got content-type "
                        f"'{content_type}' (attempt {attempt}/{max_retries})"
                    )
                else:
                    write_binary_file(filename, data)
                    break
            except urllib.error.HTTPError as http_error:
                print(f"HTTP error {http_error.code}: {http_error.reason}")
                if http_error.code == 404:
                    break
            except urllib.error.URLError as url_error:
                print(f"URL error: {url_error.reason}")

            if attempt < max_retries:
                retry_delay = random.uniform(avg_delay * 0.6, avg_delay * 1.4)
                time.sleep(retry_delay)


def make_cbz(dirname: str) -> None:
    zipname = f"{dirname}.cbz"
    images = sorted(Path(dirname).glob("*.jpg"))
    with closing(ZipFile(zipname, "w")) as zipfile:
        for filename in images:
            print(f"writing {filename} to {zipname}")
            zipfile.write(filename, arcname=filename.name)


def download_manga(
    manga_name: str,
    range_start: float = 1,
    range_end: float | None = None,
    create_cbz: bool = False,
    remove_images: bool = False,
    avg_delay: float = 2.0,
    max_retries: int = 5,
) -> None:
    chapter_urls = get_chapter_urls(manga_name)
    if range_end is None:
        range_end = max(chapter_urls.keys())

    def chapter_filter(chapter_url: tuple[float, str]) -> bool:
        return chapter_url[0] < range_start or chapter_url[0] > range_end

    for chapter, url in filterfalse(chapter_filter, chapter_urls.items()):
        print("===============================================")
        print(f"Chapter {chapter:g}")
        print("===============================================")
        image_urls = get_chapter_image_urls(url)
        download_urls(
            image_urls,
            manga_name,
            chapter,
            avg_delay=avg_delay,
            max_retries=max_retries,
        )
        download_dir = Path(".") / manga_name / f"{chapter:g}"
        if create_cbz:
            make_cbz(str(download_dir))
            if remove_images:
                shutil.rmtree(download_dir)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manga Fox Downloader")

    parser.add_argument("--manga", "-m", required=True, action="store", help="Manga to download")
    parser.add_argument(
        "--start",
        "-s",
        action="store",
        type=float,
        default=1,
        help="Chapter to start downloading from",
    )
    parser.add_argument(
        "--end",
        "-e",
        action="store",
        type=float,
        default=None,
        help="Chapter to end downloading to",
    )
    parser.add_argument(
        "--cbz",
        "-c",
        action="store_true",
        default=False,
        help="Create cbz archive after download",
    )
    parser.add_argument(
        "--remove",
        "-r",
        action="store_true",
        default=False,
        help="Remove image files after creating cbz archive",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        default=False,
        help="List available chapter numbers",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        default=False,
        help="Enable HTTP request debug logging",
    )
    parser.add_argument(
        "--delay",
        action="store",
        type=float,
        default=2.0,
        help="Average delay between image requests in seconds",
    )
    parser.add_argument(
        "--max-retries",
        action="store",
        type=int,
        default=5,
        help="Maximum retries per image",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if args.debug:
        debug_http_requests()

    if args.list:
        chapter_urls = get_chapter_urls(args.manga)
        for chapter in chapter_urls:
            print(chapter)
        return

    print(f"Getting chapters of {args.manga} from {args.start} to {args.end}")
    download_manga(
        args.manga,
        args.start,
        args.end,
        args.cbz,
        args.remove,
        args.delay,
        args.max_retries,
    )


if __name__ == "__main__":
    main()
