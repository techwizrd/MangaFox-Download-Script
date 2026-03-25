#!/usr/bin/env python3

import argparse
import concurrent.futures
import gzip
import os
import random
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
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
DESKTOP_URL_BASE = "https://fanfox.net/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": URL_BASE,
}
PROFILE_DEFAULTS = {
    "safe": {"workers": 2, "avg_delay": 2.0, "max_retries": 5},
    "balanced": {"workers": 4, "avg_delay": 1.0, "max_retries": 4},
    "aggressive": {"workers": 8, "avg_delay": 0.4, "max_retries": 3},
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


def request_url_with_headers(url: str, headers: dict[str, str]) -> urllib.request.Request:
    request_headers = {**DEFAULT_HEADERS, **headers}
    return urllib.request.Request(normalize_url(url), headers=request_headers)


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


def get_page_content_with_headers(url: str, headers: dict[str, str]) -> tuple[int, str, bytes]:
    with closing(urllib.request.urlopen(request_url_with_headers(url, headers))) as response:
        status = response.getcode()
        content_type = response.headers.get_content_type()
        payload = read_response_content(response)
        return status, content_type, payload


def get_page_soup(url: str) -> BeautifulSoup:
    _, _, page_content = get_page_content(url)
    return BeautifulSoup(page_content, "html.parser")


def manga_to_slug(manga_name: str) -> str:
    def replacer(value: str, key: str) -> str:
        return value.replace(key, "_")

    return reduce(replacer, [" ", "-"], manga_name.lower())


def get_chapter_urls(manga_name: str) -> OrderedDict[float, str]:
    manga_slug = manga_to_slug(manga_name)
    url = f"{URL_BASE}manga/{manga_slug}/"

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

    chapter_soup = get_page_soup(url_fragment)
    try:
        pages = get_page_numbers(chapter_soup)
    except SystemExit:
        return get_chapter_image_urls_desktop(url_fragment)

    chapter_base_url = os.path.dirname(url_fragment.rstrip("/")) + "/"
    image_urls: list[str] = []
    for page in pages:
        page_url = f"{chapter_base_url}{page}.html"
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


def unpack_eval_packer(source: str) -> str:
    match = re.search(r"\}\('(.*)',(\d+),(\d+),'(.*)'\.split\('\|'\),0,\{\}\)\)", source, re.S)
    if match is None:
        raise SystemExit("Error: Unable to parse chapter image payload")

    payload, base, _count, symbols = match.groups()
    base_int = int(base)
    words = symbols.split("|")

    payload = payload.replace("\\'", "'").replace("\\\\", "\\")

    def replace_token(token_match: re.Match[str]) -> str:
        token = token_match.group(0)
        try:
            index = int(token, base_int if base_int <= 36 else 36)
        except ValueError:
            return token
        if index < len(words) and words[index]:
            return words[index]
        return token

    return re.sub(r"\b\w+\b", replace_token, payload)


def get_chapter_image_urls_desktop(url_fragment: str) -> list[str]:
    chapter_url = normalize_url(url_fragment).replace("m.fanfox.net", "fanfox.net")

    _, _, chapter_content = get_page_content_with_headers(chapter_url, {"Referer": chapter_url})
    chapter_html = chapter_content.decode("utf-8", "ignore")

    chapter_id_match = re.search(r"var\s+chapterid\s*=\s*(\d+);", chapter_html)
    image_count_match = re.search(r"var\s+imagecount\s*=\s*(\d+);", chapter_html)
    if chapter_id_match is None or image_count_match is None:
        raise SystemExit("Error: Unable to parse chapter metadata")

    chapter_id = chapter_id_match.group(1)
    image_count = int(image_count_match.group(1))

    chapter_soup = BeautifulSoup(chapter_html, "html.parser")
    key_input = chapter_soup.find("input", {"id": "dm5_key"})
    key = ""
    if key_input and isinstance(key_input.get("value"), str):
        key = key_input["value"]

    chapterfun_url = urllib.parse.urljoin(DESKTOP_URL_BASE, "chapterfun.ashx")
    image_urls: list[str] = []
    for page in range(1, image_count + 1):
        query = urllib.parse.urlencode({"cid": chapter_id, "page": page, "key": key})
        request_url = f"{chapterfun_url}?{query}"
        _, _, payload = get_page_content_with_headers(
            request_url,
            {
                "Referer": chapter_url,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        unpacked = unpack_eval_packer(payload.decode("utf-8", "ignore"))

        base_match = re.search(r'var\s+pix\s*=\s*"([^"]+)";', unpacked)
        values_match = re.search(r"var\s+pvalue\s*=\s*\[(.*?)\];", unpacked, re.S)
        if base_match is None or values_match is None:
            print(f"Warning: unable to parse image payload for page {page}")
            continue

        base_path = base_match.group(1)
        values = re.findall(r'"([^"]+)"', values_match.group(1))
        if not values:
            print(f"Warning: no image values found for page {page}")
            continue

        first_value = values[0]
        if first_value.startswith("http://") or first_value.startswith("https://"):
            image_url = first_value
        elif first_value.startswith("//"):
            image_url = f"https:{first_value}"
        elif first_value.startswith("/"):
            image_url = f"{base_path}{first_value}"
        else:
            image_url = first_value

        image_urls.append(image_url)

    if not image_urls:
        raise SystemExit("Error: Unable to determine chapter image URLs")

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
    workers: int = 1,
) -> None:
    image_list = list(image_urls)
    chapter_label = f"{chapter_number:g}"
    download_dir = Path(manga_name) / chapter_label
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True)

    random.seed()

    def download_image(index: int, url: str) -> None:
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

    with tqdm(
        total=len(image_list),
        desc=f"Chapter {chapter_label}",
        unit="img",
        disable=not sys.stderr.isatty(),
    ) as progress:
        if workers == 1:
            for index, url in enumerate(image_list):
                download_image(index, url)
                progress.update(1)
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(download_image, index, url) for index, url in enumerate(image_list)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
                progress.update(1)


def make_cbz(dirname: str) -> None:
    zipname = f"{dirname}.cbz"
    images = sorted(Path(dirname).glob("*.jpg"))
    with closing(ZipFile(zipname, "w")) as zipfile:
        for filename in images:
            zipfile.write(filename, arcname=filename.name)


def download_manga(
    manga_name: str,
    range_start: float = 1,
    range_end: float | None = None,
    create_cbz: bool = False,
    remove_images: bool = False,
    force: bool = False,
    avg_delay: float = 2.0,
    max_retries: int = 5,
    workers: int = 1,
) -> None:
    chapter_urls = get_chapter_urls(manga_name)
    if range_end is None:
        range_end = max(chapter_urls.keys())

    def chapter_filter(chapter_url: tuple[float, str]) -> bool:
        return chapter_url[0] < range_start or chapter_url[0] > range_end

    for chapter, url in filterfalse(chapter_filter, chapter_urls.items()):
        chapter_cbz = Path(manga_name) / f"{chapter:g}.cbz"
        if chapter_cbz.exists() and not force:
            print(f"Skipping chapter {chapter:g} (already downloaded)")
            continue

        image_urls = get_chapter_image_urls(url)
        download_urls(
            image_urls,
            manga_name,
            chapter,
            avg_delay=avg_delay,
            max_retries=max_retries,
            workers=workers,
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
        "--force",
        "-f",
        action="store_true",
        default=False,
        help="Redownload chapters even if matching cbz files already exist",
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
        "--profile",
        action="store",
        choices=sorted(PROFILE_DEFAULTS.keys()),
        default="safe",
        help="Performance profile (safe is default)",
    )
    parser.add_argument(
        "--workers",
        action="store",
        type=int,
        default=None,
        help="Concurrent image downloads (overrides profile)",
    )
    parser.add_argument(
        "--delay",
        action="store",
        type=float,
        default=None,
        help="Average delay between retry attempts in seconds (overrides profile)",
    )
    parser.add_argument(
        "--max-retries",
        action="store",
        type=int,
        default=None,
        help="Maximum retries per image (overrides profile)",
    )

    return parser.parse_args()


def resolve_runtime_settings(args: argparse.Namespace) -> tuple[float, int, int]:
    profile_settings = PROFILE_DEFAULTS[args.profile]

    avg_delay = float(args.delay if args.delay is not None else profile_settings["avg_delay"])
    max_retries = int(
        args.max_retries if args.max_retries is not None else profile_settings["max_retries"]
    )
    workers = int(args.workers if args.workers is not None else profile_settings["workers"])

    if avg_delay < 0:
        raise SystemExit("Error: --delay must be >= 0")
    if max_retries < 1:
        raise SystemExit("Error: --max-retries must be >= 1")
    if workers < 1:
        raise SystemExit("Error: --workers must be >= 1")

    return avg_delay, max_retries, workers


def main() -> None:
    args = parse_arguments()

    if args.debug:
        debug_http_requests()

    if args.list:
        chapter_urls = get_chapter_urls(args.manga)
        for chapter in chapter_urls:
            print(chapter)
        return

    avg_delay, max_retries, workers = resolve_runtime_settings(args)

    download_manga(
        args.manga,
        args.start,
        args.end,
        args.cbz,
        args.remove,
        args.force,
        avg_delay,
        max_retries,
        workers,
    )


if __name__ == "__main__":
    main()
