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
