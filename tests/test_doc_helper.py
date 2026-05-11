"""Тести для _doc() хелпера та sw_open_document (без COM)."""
import pytest
import server


class TestDocHelper:
    def test_raises_when_swapp_is_none(self):
        server.swApp = None
        with pytest.raises((RuntimeError, AttributeError)):
            server._doc()

    def test_raises_when_active_doc_is_none(self):
        class FakeApp:
            ActiveDoc = None

        server.swApp = FakeApp()
        with pytest.raises(RuntimeError, match="Немає активного документа"):
            server._doc()

    def test_returns_active_doc(self):
        class FakeDoc:
            pass

        class FakeApp:
            ActiveDoc = FakeDoc()

        server.swApp = FakeApp()
        assert server._doc() is FakeApp.ActiveDoc


class TestSwOpenDocument:
    def test_returns_error_when_file_not_found(self):
        server.swApp = object()
        result = server.sw_open_document("/nonexistent/path/file.sldprt")
        assert "не знайдено" in result
        assert "/nonexistent/path/file.sldprt" in result

    def test_missing_file_does_not_call_com(self, mocker):
        server.swApp = mocker.MagicMock()
        server.sw_open_document("/does/not/exist.sldprt")
        server.swApp.OpenDoc6.assert_not_called()
