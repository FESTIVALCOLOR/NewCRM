"""
Backend Tests — блок сайта «Пример проекта»: проверка PDF и подготовка страниц-картинок.
PDF собирается прямо в тесте, сервер и сеть не нужны.
"""

import io
from pathlib import Path
import sys

import pytest

pdfium = pytest.importorskip("pypdfium2")
Image = pytest.importorskip("PIL.Image")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

from services import site_example_project as ex  # noqa: E402


def make_pdf(sizes) -> bytes:
    document = pdfium.PdfDocument.new()
    for width, height in sizes:
        document.new_page(width, height)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


A3_LANDSCAPE = (1191, 842)
A4_PORTRAIT = (595, 842)


@pytest.mark.backend
class TestCheckPdf:
    def test_page_count(self):
        assert ex.check_pdf(make_pdf([A3_LANDSCAPE] * 3)) == 3

    @pytest.mark.parametrize("content, message", [(b"GIF89a....", "не PDF"), (b"%PDF-1.7 broken", "открыть")])
    def test_not_a_pdf(self, content, message):
        with pytest.raises(ex.ExampleProjectError, match=message):
            ex.check_pdf(content)

    def test_too_big(self, monkeypatch):
        monkeypatch.setattr(ex, "MAX_PDF_BYTES", 10)
        with pytest.raises(ex.ExampleProjectError, match="большой"):
            ex.check_pdf(b"%PDF" + b"0" * 20)

    def test_too_many_pages(self, monkeypatch):
        monkeypatch.setattr(ex, "MAX_PAGES", 2)
        with pytest.raises(ex.ExampleProjectError, match="не больше 2"):
            ex.check_pdf(make_pdf([A4_PORTRAIT] * 3))


@pytest.mark.backend
class TestRenderPages:
    def test_pages_become_jpeg_with_long_side_limit(self, tmp_path):
        pdf = tmp_path / "p.pdf"
        pdf.write_bytes(make_pdf([A3_LANDSCAPE, A4_PORTRAIT]))
        progress = []
        urls, width, height = ex.render_pages(str(pdf), str(tmp_path), "tok", lambda done, total: progress.append((done, total)))
        assert urls == [ex.MEDIA_PREFIX + "tok-p001.jpg", ex.MEDIA_PREFIX + "tok-p002.jpg"]
        # Размер книги — по первой странице: альбомный A3, длинная сторона 1600
        assert width == ex.PAGE_LONG_SIDE and abs(height - round(1600 * 842 / 1191)) <= 1
        with Image.open(tmp_path / "tok-p002.jpg") as second:
            assert second.format == "JPEG" and max(second.size) == ex.PAGE_LONG_SIDE and second.size[1] > second.size[0]
        assert progress == [(1, 2), (2, 2)]


@pytest.mark.backend
class TestFiles:
    def test_media_files_of_project(self):
        project = {"pages": [ex.MEDIA_PREFIX + "a-p001.jpg", "https://elsewhere/x.jpg"], "pdf": ex.MEDIA_PREFIX + "a.pdf"}
        assert ex._media_files(project) == ["a-p001.jpg", "a.pdf"]
        assert ex._media_files(None) == []

    def test_remove_never_leaves_uploads_dir(self, tmp_path):
        uploads = tmp_path / "uploads"
        uploads.mkdir()
        (uploads / "a.pdf").write_bytes(b"x")
        outside = tmp_path / "secret.txt"
        outside.write_text("keep")
        ex._remove_files(str(uploads), ["a.pdf", "../secret.txt", "..\\secret.txt", ".env", "missing.jpg"])
        assert not (uploads / "a.pdf").exists()
        assert outside.read_text() == "keep"
