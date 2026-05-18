"""Тести для sw_new_assembly, sw_add_component, sw_add_mate, sw_list_components, sw_save_assembly."""
import os
import pytest
from unittest.mock import MagicMock, patch
import server


# ──────────────────────────────────────────────────────────────
# sw_new_assembly
# ──────────────────────────────────────────────────────────────

class TestSwNewAssembly:
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
                server.sw_new_assembly()

    def test_uses_preference_path_when_valid(self):
        app = self._setup_app(preference_path=r"C:\templates\Assembly.ASMDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument") as mock_new:
                server.sw_new_assembly()
                mock_new.assert_called_once_with(r"C:\templates\Assembly.ASMDOT", 0, 0, 0)

    def test_falls_back_to_candidate(self):
        app = self._setup_app(preference_path="")
        candidate = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Assembly.ASMDOT"

        def exists_side_effect(path):
            return path == candidate

        with patch("os.path.exists", side_effect=exists_side_effect):
            with patch.object(app, "NewDocument") as mock_new:
                result = server.sw_new_assembly()
                mock_new.assert_called_once_with(candidate, 0, 0, 0)
                assert "збірка" in result.lower()

    def test_result_mentions_assembly(self):
        app = self._setup_app(preference_path=r"C:\templates\Assembly.ASMDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument"):
                result = server.sw_new_assembly()
                assert "збірк" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_add_component
# ──────────────────────────────────────────────────────────────

class TestSwAddComponent:
    def _setup_doc(self, add_component_return=None):
        mock_doc = MagicMock()
        mock_doc.AddComponent5.return_value = add_component_return

        class FakeApp:
            ActiveDoc = mock_doc

        server._sw = lambda: FakeApp()
        return mock_doc

    def test_returns_error_when_file_not_found(self):
        self._setup_doc()
        result = server.sw_add_component("/nonexistent/part.sldprt")
        assert "не знайдено" in result

    def test_does_not_call_com_when_file_missing(self):
        doc = self._setup_doc()
        server.sw_add_component("/nonexistent/part.sldprt")
        doc.AddComponent5.assert_not_called()

    def test_converts_mm_to_m(self, mocker):
        doc = self._setup_doc(add_component_return=mocker.MagicMock())
        with patch("os.path.exists", return_value=True):
            server.sw_add_component(r"C:\work\part.sldprt", 10.0, 20.0, 30.0)
        _, _, _, _, _, x, y, z = doc.AddComponent5.call_args[0]
        assert x == pytest.approx(0.010)
        assert y == pytest.approx(0.020)
        assert z == pytest.approx(0.030)

    def test_raises_when_add_component_fails(self):
        self._setup_doc(add_component_return=None)
        with patch("os.path.exists", return_value=True):
            with pytest.raises(RuntimeError):
                server.sw_add_component(r"C:\work\part.sldprt")

    def test_result_contains_filename(self, mocker):
        self._setup_doc(add_component_return=mocker.MagicMock())
        with patch("os.path.exists", return_value=True):
            result = server.sw_add_component(r"C:\work\bracket.sldprt")
        assert "bracket.sldprt" in result

    def test_default_position_is_origin(self, mocker):
        doc = self._setup_doc(add_component_return=mocker.MagicMock())
        with patch("os.path.exists", return_value=True):
            server.sw_add_component(r"C:\work\part.sldprt")
        _, _, _, _, _, x, y, z = doc.AddComponent5.call_args[0]
        assert x == 0.0
        assert y == 0.0
        assert z == 0.0


# ──────────────────────────────────────────────────────────────
# sw_add_mate
# ──────────────────────────────────────────────────────────────

class TestSwAddMate:
    def _setup_doc(self, mate_return=None):
        mock_fm = MagicMock()
        mock_fm.InsertMate5.return_value = mate_return

        class FakeDoc:
            FeatureManager = mock_fm

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        return mock_fm

    def test_coincident_passes_0(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("coincident")
        assert fm.InsertMate5.call_args[0][0] == 0

    def test_parallel_passes_1(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("parallel")
        assert fm.InsertMate5.call_args[0][0] == 1

    def test_perpendicular_passes_2(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("perpendicular")
        assert fm.InsertMate5.call_args[0][0] == 2

    def test_concentric_passes_4(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("concentric")
        assert fm.InsertMate5.call_args[0][0] == 4

    def test_unknown_type_defaults_to_coincident(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("unknown_type")
        assert fm.InsertMate5.call_args[0][0] == 0

    def test_raises_when_mate_fails(self):
        self._setup_doc(mate_return=None)
        with pytest.raises(RuntimeError):
            server.sw_add_mate("coincident")

    def test_result_contains_mate_type(self, mocker):
        self._setup_doc(mate_return=mocker.MagicMock())
        result = server.sw_add_mate("parallel")
        assert "parallel" in result

    def test_result_mentions_both_entities(self, mocker):
        self._setup_doc(mate_return=mocker.MagicMock())
        result = server.sw_add_mate("distance")
        assert "distance" in result


# ──────────────────────────────────────────────────────────────
# sw_list_components
# ──────────────────────────────────────────────────────────────

class TestSwListComponents:
    def _setup(self, comps):
        mock_doc = MagicMock()
        mock_doc.GetComponents.return_value = comps

        class FakeApp:
            ActiveDoc = mock_doc

        server._sw = lambda: FakeApp()

    def test_empty_assembly(self):
        self._setup([])
        result = server.sw_list_components()
        assert "порожня" in result

    def test_lists_component_names(self):
        comp = MagicMock()
        comp.Name2 = "Body-1"
        comp.GetPathName.return_value = r"C:\work\body.sldprt"
        comp.IsSuppressed.return_value = False
        self._setup([comp])
        result = server.sw_list_components()
        assert "Body-1" in result
        assert "body.sldprt" in result

    def test_suppressed_marked(self):
        comp = MagicMock()
        comp.Name2 = "Clip-1"
        comp.GetPathName.return_value = ""
        comp.IsSuppressed.return_value = True
        self._setup([comp])
        result = server.sw_list_components()
        assert "[придушено]" in result

    def test_component_count_in_result(self):
        comps = [MagicMock(Name2="P", IsSuppressed=MagicMock(return_value=False),
                           GetPathName=MagicMock(return_value="")) for _ in range(3)]
        self._setup(comps)
        result = server.sw_list_components()
        assert "3" in result


# ──────────────────────────────────────────────────────────────
# sw_save_assembly
# ──────────────────────────────────────────────────────────────

class TestSwSaveAssembly:
    def _setup(self):
        mock_doc = MagicMock()

        class FakeApp:
            ActiveDoc = mock_doc

        server._sw = lambda: FakeApp()
        return mock_doc

    def test_save_calls_save_as3(self):
        doc = self._setup()
        server.sw_save_assembly(r"C:\work\drever.sldasm")
        doc.SaveAs3.assert_called_once_with(r"C:\work\drever.sldasm", 0, 2)

    def test_result_contains_path(self):
        self._setup()
        result = server.sw_save_assembly(r"C:\work\drever.sldasm")
        assert "drever.sldasm" in result
