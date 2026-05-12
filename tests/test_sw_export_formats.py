"""Тести для sw_export_step, sw_export_iges, sw_export_pdf."""
import pytest
import server


def _setup_doc(mocker):
    mock_doc = mocker.MagicMock()
    mock_doc.SaveAs3.return_value = None

    class FakeApp:
        ActiveDoc = mock_doc

    server._sw = lambda: FakeApp()
    return mock_doc


# ──────────────────────────────────────────────────────────────
# sw_export_step
# ──────────────────────────────────────────────────────────────

class TestSwExportStep:
    def test_calls_save_as3(self, mocker):
        doc = _setup_doc(mocker)
        server.sw_export_step(r"C:\work\part.step")
        doc.SaveAs3.assert_called_once_with(r"C:\work\part.step", 0, 2)

    def test_result_contains_filepath(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_step(r"C:\work\part.step")
        assert r"C:\work\part.step" in result

    def test_result_mentions_step(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_step(r"C:\work\part.step")
        assert "STEP" in result or "step" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_export_iges
# ──────────────────────────────────────────────────────────────

class TestSwExportIges:
    def test_calls_save_as3(self, mocker):
        doc = _setup_doc(mocker)
        server.sw_export_iges(r"C:\work\part.igs")
        doc.SaveAs3.assert_called_once_with(r"C:\work\part.igs", 0, 2)

    def test_result_contains_filepath(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_iges(r"C:\work\part.igs")
        assert r"C:\work\part.igs" in result

    def test_result_mentions_iges(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_iges(r"C:\work\part.igs")
        assert "IGES" in result or "iges" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_export_pdf
# ──────────────────────────────────────────────────────────────

class TestSwExportPdf:
    def test_calls_save_as3(self, mocker):
        doc = _setup_doc(mocker)
        server.sw_export_pdf(r"C:\work\drawing.pdf")
        doc.SaveAs3.assert_called_once_with(r"C:\work\drawing.pdf", 0, 2)

    def test_result_contains_filepath(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_pdf(r"C:\work\drawing.pdf")
        assert r"C:\work\drawing.pdf" in result

    def test_result_mentions_pdf(self, mocker):
        _setup_doc(mocker)
        result = server.sw_export_pdf(r"C:\work\drawing.pdf")
        assert "PDF" in result or "pdf" in result.lower()
