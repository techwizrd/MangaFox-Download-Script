import argparse
import urllib.parse
from email.message import Message
from pathlib import Path
from zipfile import ZipFile

import pytest
from bs4 import BeautifulSoup

import mfdl


def test_get_chapter_number_from_url() -> None:
    assert mfdl.get_chapter_number("/manga/demo/v01/c007/1.html") == 7.0
    assert mfdl.get_chapter_number("https://m.fanfox.net/manga/demo/c12.5/1.html") == 12.5
    assert mfdl.get_chapter_number("/manga/demo/") is None


def test_get_page_numbers_modern_markup() -> None:
    soup = BeautifulSoup(
        """
        <select class='mangaread-page'>
          <option>1</option>
          <option>2</option>
          <option>3</option>
        </select>
        """,
        "html.parser",
    )
    assert mfdl.get_page_numbers(soup) == [1, 2, 3]


def test_get_page_numbers_legacy_markup() -> None:
    soup = BeautifulSoup(
        """
        <select class='m'>
          <option value='1'>1</option>
          <option value='2'>2</option>
        </select>
        """,
        "html.parser",
    )
    assert mfdl.get_page_numbers(soup) == [1, 2]


def test_make_cbz_flattens_paths(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "Demo" / "1"
    chapter_dir.mkdir(parents=True)
    image_path = chapter_dir / "000.jpg"
    image_path.write_bytes(b"img")

    mfdl.make_cbz(str(chapter_dir))

    with ZipFile(str(chapter_dir) + ".cbz") as archive:
        assert archive.namelist() == ["000.jpg"]


def test_download_urls_retries_until_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mfdl.time, "sleep", lambda _: None)
    monkeypatch.setattr(mfdl.random, "uniform", lambda _a, _b: 0.0)

    responses = [
        (200, "text/html", b"<html>maintenance</html>"),
        (200, "image/jpeg", b"jpegbytes"),
    ]

    def fake_get_page_content(_url: str) -> tuple[int, str, bytes]:
        return responses.pop(0)

    monkeypatch.setattr(mfdl, "get_page_content", fake_get_page_content)

    mfdl.download_urls(["https://cdn.example/1.jpg"], "Demo", 1.0, avg_delay=0.0, max_retries=3)

    assert (tmp_path / "Demo" / "1" / "000.jpg").read_bytes() == b"jpegbytes"


def test_download_urls_skips_404(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mfdl.time, "sleep", lambda _: None)

    def fake_get_page_content(_url: str) -> tuple[int, str, bytes]:
        raise mfdl.urllib.error.HTTPError(_url, 404, "Not Found", Message(), None)

    monkeypatch.setattr(mfdl, "get_page_content", fake_get_page_content)

    mfdl.download_urls(["https://cdn.example/1.jpg"], "Demo", 1.0, avg_delay=0.0, max_retries=3)

    assert not (tmp_path / "Demo" / "1" / "000.jpg").exists()


def test_unpack_eval_packer_extracts_payload() -> None:
    packed = (
        'eval(function(p,a,c,k,e,d){e=function(c){return(c<a?"":'
        "+e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};"
        "if(!''.replace(/^/,String)){while(c--)d[e(c)]=k[c]||e(c);"
        "k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1;};"
        "while(c--)if(k[c])p=p.replace(new RegExp('\\\\b'+e(c)+'\\\\b','g'),k[c]);"
        'return p;}(\'0 1="//2";0 3=["/4"];\',5,5,'
        "'var|pix|cdn|pvalue|a.jpg'.split('|'),0,{}))"
    )

    unpacked = mfdl.unpack_eval_packer(packed)

    assert unpacked == 'var pix="//cdn";var pvalue=["/a.jpg"];'


def test_get_chapter_image_urls_falls_back_to_desktop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mfdl, "get_page_soup", lambda _url: BeautifulSoup("<html></html>", "html.parser")
    )
    monkeypatch.setattr(
        mfdl,
        "get_chapter_image_urls_desktop",
        lambda _fragment: ["https://img.example/001.jpg"],
    )

    image_urls = mfdl.get_chapter_image_urls("//m.fanfox.net/manga/demo/v01/c001/1.html")

    assert image_urls == ["https://img.example/001.jpg"]


def test_get_chapter_image_urls_desktop_parses_api_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    chapter_html = """
    <html>
      <body>
        <input id="dm5_key" value="demo-key" />
        <script>var chapterid =398501; var imagecount=2;</script>
      </body>
    </html>
    """
    unpacked_by_page = {
        1: 'var pix="https://cdn.example/base";var pvalue=["/p1.jpg"];',
        2: 'var pix="https://cdn.example/base";var pvalue=["//img.example/p2.jpg"];',
    }
    api_calls: list[tuple[dict[str, str], dict[str, list[str]]]] = []

    def fake_get_page_content_with_headers(
        url: str,
        headers: dict[str, str],
    ) -> tuple[int, str, bytes]:
        if "chapterfun.ashx" not in url:
            return 200, "text/html", chapter_html.encode()

        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        api_calls.append((headers, query))
        page = int(query["page"][0])
        return 200, "text/plain", f"packed-page-{page}".encode()

    def fake_unpack_eval_packer(payload: str) -> str:
        page = int(payload.rsplit("-", 1)[-1])
        return unpacked_by_page[page]

    monkeypatch.setattr(mfdl, "get_page_content_with_headers", fake_get_page_content_with_headers)
    monkeypatch.setattr(mfdl, "unpack_eval_packer", fake_unpack_eval_packer)

    image_urls = mfdl.get_chapter_image_urls_desktop("//m.fanfox.net/manga/demo/v01/c001/1.html")

    assert image_urls == [
        "https://cdn.example/base/p1.jpg",
        "https://img.example/p2.jpg",
    ]
    assert len(api_calls) == 2
    assert all(headers.get("X-Requested-With") == "XMLHttpRequest" for headers, _ in api_calls)
    assert all(query["cid"] == ["398501"] for _, query in api_calls)
    assert all(query["key"] == ["demo-key"] for _, query in api_calls)


def test_resolve_runtime_settings_safe_defaults() -> None:
    args = argparse.Namespace(
        profile="safe",
        delay=None,
        max_retries=None,
        workers=None,
    )

    assert mfdl.resolve_runtime_settings(args) == (2.0, 5, 2)


def test_resolve_runtime_settings_workers_override_profile() -> None:
    args = argparse.Namespace(
        profile="balanced",
        delay=None,
        max_retries=None,
        workers=6,
    )

    avg_delay, max_retries, workers = mfdl.resolve_runtime_settings(args)

    assert avg_delay == 1.0
    assert max_retries == 4
    assert workers == 6


def test_download_manga_skips_existing_cbz_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Demo").mkdir()
    (tmp_path / "Demo" / "1.cbz").write_bytes(b"existing")

    monkeypatch.setattr(
        mfdl,
        "get_chapter_urls",
        lambda _manga: mfdl.OrderedDict([(1.0, "/demo/c001/1.html"), (2.0, "/demo/c002/1.html")]),
    )
    monkeypatch.setattr(mfdl, "get_chapter_image_urls", lambda _url: ["https://img.example/1.jpg"])

    downloaded_chapters: list[float] = []

    def fake_download_urls(
        _image_urls: list[str],
        _manga_name: str,
        chapter_number: float,
        **_kwargs: float | int,
    ) -> None:
        downloaded_chapters.append(chapter_number)

    monkeypatch.setattr(mfdl, "download_urls", fake_download_urls)

    mfdl.download_manga("Demo")

    assert downloaded_chapters == [2.0]


def test_download_manga_force_redownloads_existing_cbz(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Demo").mkdir()
    (tmp_path / "Demo" / "1.cbz").write_bytes(b"existing")

    monkeypatch.setattr(
        mfdl,
        "get_chapter_urls",
        lambda _manga: mfdl.OrderedDict([(1.0, "/demo/c001/1.html"), (2.0, "/demo/c002/1.html")]),
    )
    monkeypatch.setattr(mfdl, "get_chapter_image_urls", lambda _url: ["https://img.example/1.jpg"])

    downloaded_chapters: list[float] = []

    def fake_download_urls(
        _image_urls: list[str],
        _manga_name: str,
        chapter_number: float,
        **_kwargs: float | int,
    ) -> None:
        downloaded_chapters.append(chapter_number)

    monkeypatch.setattr(mfdl, "download_urls", fake_download_urls)

    mfdl.download_manga("Demo", force=True)

    assert downloaded_chapters == [1.0, 2.0]
