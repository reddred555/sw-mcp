"""Тести для sw_new_drawing та sw_add_drawing_view."""
import pytest
from unittest.mock import patch, MagicMock
import server


# ──────────────────────────────────────────────────────────────
# sw_new_drawing
# ──────────────────────────────────────────────────────────────

class TestSwNewDrawing:
    def _setup_app(self, preference_path=""):
        class FakeApp:
            def GetUserPreferenceStringValue(self_, key):
                return preference_path
            NewDocument = MagicMock()

        app = FakeApp()
        server._sw = lambda: app
        return app

    def test_raises_when_no_template_found(self):
        self._setup_app(preference_path="")
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Шаблон"):
                server.sw_new_drawing()

    def test_uses_preference_path_when_valid(self):
        app = self._setup_app(preference_path=r"C:\templates\Drawing.DRWDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument") as mock_new:
                server.sw_new_drawing()
                mock_new.assert_called_once_with(r"C:\templates\Drawing.DRWDOT", 0, 0, 0)

    def test_falls_back_to_candidate(self):
        app = self._setup_app(preference_path="")
        candidate = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Drawing.DRWDOT"

        def exists_side_effect(path):
            return path == candidate

        with patch("os.path.exists", side_effect=exists_side_effect):
            with patch.object(app, "NewDocument") as mock_new:
                result = server.sw_new_drawing()
                mock_new.assert_called_once_with(candidate, 0, 0, 0)
                assert "креслення" in result.lower()

    def test_result_mentions_drawing(self):
        app = self._setup_app(preference_path=r"C:\templates\Drawing.DRWDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument"):
                result = server.sw_new_drawing()
                assert "креслення" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_add_drawing_view
# ──────────────────────────────────────────────────────────────

class TestSwAddDrawingView:
    def _setup_doc(self, view_return=None):
        mock_doc = MagicMock()
        mock_doc.CreateDrawViewFromModelView3.return_value = view_return

        class FakeApp:
            ActiveDoc = mock_doc

        server._sw = lambda: FakeApp()
        return mock_doc

    def test_front_maps_to_star_front(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="front")
        _, view_name, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert view_name == "*Front"

    def test_top_maps_to_star_top(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="top")
        _, view_name, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert view_name == "*Top"

    def test_right_maps_to_star_right(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="right")
        _, view_name, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert view_name == "*Right"

    def test_isometric_maps_to_star_isometric(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="isometric")
        _, view_name, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert view_name == "*Isometric"

    def test_unknown_view_defaults_to_front(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="diagonal")
        _, view_name, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert view_name == "*Front"

    def test_converts_mm_to_m(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\part.sldprt", x_mm=100.0, y_mm=200.0)
        _, _, x, y, _ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert x == pytest.approx(0.100)
        assert y == pytest.approx(0.200)

    def test_passes_model_path(self, mocker):
        doc = self._setup_doc(view_return=mocker.MagicMock())
        server.sw_add_drawing_view(r"C:\work\bracket.sldprt")
        model_path, *_ = doc.CreateDrawViewFromModelView3.call_args[0]
        assert model_path == r"C:\work\bracket.sldprt"

    def test_raises_when_view_creation_fails(self):
        self._setup_doc(view_return=None)
        with pytest.raises(RuntimeError):
            server.sw_add_drawing_view(r"C:\work\part.sldprt")

    def test_result_contains_view_type(self, mocker):
        self._setup_doc(view_return=mocker.MagicMock())
        result = server.sw_add_drawing_view(r"C:\work\part.sldprt", view_type="isometric")
        assert "isometric" in result
