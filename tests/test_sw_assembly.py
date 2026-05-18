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
        server.swApp = app
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

        server.swApp = FakeApp()
        return mock_doc

    def test_returns_error_when_file_not_found(self):
        self._setup_doc()
        result = server.sw_add_component("/nonexistent/part.sldprt")
        assert "не знайдено" in result

    def test_does_not_call_com_when_file_missing(self):
        doc = self._setup_doc()
        server.sw_add_component("/nonexistent/part.sldprt")
        doc.AddComponent5.assert_not_called()

    def test_converts_mm_to_m(self, mocker, tmp_path):
        f = tmp_path / "part.sldprt"
        f.write_text("")
        doc = self._setup_doc(add_component_return=mocker.MagicMock())
        server.sw_add_component(str(f), 10.0, 20.0, 30.0)
        args = doc.AddComponent5.call_args[0]
        # last 3 positional args are x, y, z in metres
        assert args[-3] == pytest.approx(0.010)
        assert args[-2] == pytest.approx(0.020)
        assert args[-1] == pytest.approx(0.030)

    def test_default_position_is_origin(self, mocker, tmp_path):
        f = tmp_path / "part.sldprt"
        f.write_text("")
        doc = self._setup_doc(add_component_return=mocker.MagicMock())
        server.sw_add_component(str(f))
        args = doc.AddComponent5.call_args[0]
        assert args[-3] == 0.0
        assert args[-2] == 0.0
        assert args[-1] == 0.0

    def test_raises_when_add_component_fails(self, tmp_path):
        f = tmp_path / "part.sldprt"
        f.write_text("")
        self._setup_doc(add_component_return=None)
        with pytest.raises(RuntimeError):
            server.sw_add_component(str(f))

    def test_result_contains_filename(self, mocker, tmp_path):
        f = tmp_path / "bracket.sldprt"
        f.write_text("")
        self._setup_doc(add_component_return=mocker.MagicMock())
        result = server.sw_add_component(str(f))
        assert "bracket.sldprt" in result

    def test_position_shown_in_result(self, mocker, tmp_path):
        f = tmp_path / "cap.sldprt"
        f.write_text("")
        self._setup_doc(add_component_return=mocker.MagicMock())
        result = server.sw_add_component(str(f), x_mm=10.0, y_mm=20.0, z_mm=5.0)
        assert "10.0" in result and "20.0" in result and "5.0" in result


# ──────────────────────────────────────────────────────────────
# sw_add_mate
# ──────────────────────────────────────────────────────────────

class TestSwAddMate:
    def _setup_doc(self, mate_return=None):
        mock_fm = MagicMock()
        mock_fm.InsertMate5.return_value = mate_return
        mock_doc = MagicMock()
        mock_doc.FeatureManager = mock_fm

        class FakeApp:
            ActiveDoc = mock_doc

        server.swApp = FakeApp()
        return mock_fm

    # ── correct swMateType_e codes ──────────────────────────

    def test_coincident_passes_code_0(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("coincident")
        assert fm.InsertMate5.call_args[0][0] == 0

    def test_parallel_passes_code_1(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("parallel")
        assert fm.InsertMate5.call_args[0][0] == 1

    def test_perpendicular_passes_code_2(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("perpendicular")
        assert fm.InsertMate5.call_args[0][0] == 2

    def test_concentric_passes_code_4(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("concentric")
        assert fm.InsertMate5.call_args[0][0] == 4

    def test_distance_passes_code_5(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("distance")
        assert fm.InsertMate5.call_args[0][0] == 5

    def test_angle_passes_code_6(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("angle")
        assert fm.InsertMate5.call_args[0][0] == 6

    def test_unknown_type_defaults_to_coincident(self, mocker):
        fm = self._setup_doc(mate_return=mocker.MagicMock())
        server.sw_add_mate("unknown_type")
        assert fm.InsertMate5.call_args[0][0] == 0

    # ── error handling ──────────────────────────────────────

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
        result = server.sw_add_mate("distance", "EntityA", "EntityB")
        assert "EntityA" in result and "EntityB" in result


# ──────────────────────────────────────────────────────────────
# sw_list_components
# ──────────────────────────────────────────────────────────────

class TestSwListComponents:
    def test_empty_assembly(self):
        class FakeAsm:
            def GetComponents(self, _): return []

        class FakeApp:
            ActiveDoc = FakeAsm()

        server.swApp = FakeApp()
        result = server.sw_list_components()
        assert "порожня" in result

    def test_lists_component_names(self):
        class FakeComp:
            Name2 = "Body-1"
            def GetPathName(self): return r"C:\work\body.sldprt"
            def IsSuppressed(self): return False

        class FakeAsm:
            def GetComponents(self, _): return [FakeComp()]

        class FakeApp:
            ActiveDoc = FakeAsm()

        server.swApp = FakeApp()
        result = server.sw_list_components()
        assert "Body-1" in result
        assert "body.sldprt" in result

    def test_suppressed_marked(self):
        class FakeComp:
            Name2 = "Clip-1"
            def GetPathName(self): return ""
            def IsSuppressed(self): return True

        class FakeAsm:
            def GetComponents(self, _): return [FakeComp()]

        class FakeApp:
            ActiveDoc = FakeAsm()

        server.swApp = FakeApp()
        result = server.sw_list_components()
        assert "[придушено]" in result

    def test_component_count_in_result(self):
        class FakeComp:
            Name2 = "P"
            def GetPathName(self): return ""
            def IsSuppressed(self): return False

        class FakeAsm:
            def GetComponents(self, _): return [FakeComp(), FakeComp(), FakeComp()]

        class FakeApp:
            ActiveDoc = FakeAsm()

        server.swApp = FakeApp()
        result = server.sw_list_components()
        assert "3" in result


# ──────────────────────────────────────────────────────────────
# sw_save_assembly
# ──────────────────────────────────────────────────────────────

class TestSwSaveAssembly:
    def test_save_calls_save_as3(self):
        asm = MagicMock()

        class FakeApp:
            ActiveDoc = asm

        server.swApp = FakeApp()
        server.sw_save_assembly(r"C:\work\drever.sldasm")
        asm.SaveAs3.assert_called_once_with(r"C:\work\drever.sldasm", 0, 2)

    def test_result_contains_path(self):
        asm = MagicMock()

        class FakeApp:
            ActiveDoc = asm

        server.swApp = FakeApp()
        result = server.sw_save_assembly(r"C:\work\drever.sldasm")
        assert "drever.sldasm" in result
