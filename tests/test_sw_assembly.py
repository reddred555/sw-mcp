"""Тести для sw_new_assembly, sw_add_component, sw_add_mate, sw_list_components."""
import os
import pytest
from unittest.mock import MagicMock, patch
import server


def _setup_asm(comps=None):
    class FakeComp:
        def __init__(self, name, path="", suppressed=False):
            self.Name2 = name
            self._path = path
            self._supp = suppressed

        def GetPathName(self):
            return self._path

        def IsSuppressed(self):
            return self._supp

    class FakeAsm:
        Extension = MagicMock()

        def __init__(self, comps):
            self._comps = comps

        def GetComponents(self, top_only):
            return self._comps

        def AddComponent4(self, path, cfg, x, y, z):
            if path == "__fail__":
                return None
            c = FakeComp(os.path.basename(path), path)
            self._comps.append(c)
            return c

        def FeatureManager(self):
            pass

        def SaveAs3(self, path, *_):
            self._saved = path

    class FakeApp:
        ActiveDoc = FakeAsm(comps or [])

    server.swApp = FakeApp()
    return FakeApp.ActiveDoc


# ─── sw_new_assembly ───────────────────────────────────────────

class TestSwNewAssembly:
    def _setup_app(self, pref_path=""):
        class FakeApp:
            def GetUserPreferenceStringValue(self_, key):
                return pref_path
            NewDocument = MagicMock()

        app = FakeApp()
        server.swApp = app
        return app

    def test_raises_when_no_template(self):
        self._setup_app(pref_path="")
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Assembly"):
                server.sw_new_assembly()

    def test_uses_preference_path(self):
        app = self._setup_app(pref_path=r"C:\templates\Assembly.ASMDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument") as mock_new:
                server.sw_new_assembly()
                mock_new.assert_called_once_with(r"C:\templates\Assembly.ASMDOT", 1, 0, 0)

    def test_fallback_to_candidate(self):
        self._setup_app(pref_path="")
        candidate = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Assembly.ASMDOT"

        def exists_side(p):
            return p == candidate

        with patch("os.path.exists", side_effect=exists_side):
            result = server.sw_new_assembly()
            assert "Нова збірка" in result

    def test_result_message(self):
        app = self._setup_app(pref_path=r"C:\t\Assembly.ASMDOT")
        with patch("os.path.exists", return_value=True):
            result = server.sw_new_assembly()
            assert "збірка" in result.lower()


# ─── sw_add_component ──────────────────────────────────────────

class TestSwAddComponent:
    def test_missing_file_returns_error(self):
        _setup_asm()
        result = server.sw_add_component("/no/such/part.sldprt")
        assert "не знайдено" in result

    def test_missing_file_no_com_call(self, mocker):
        asm = _setup_asm()
        spy = mocker.patch.object(asm, "AddComponent4")
        server.sw_add_component("/no/such.sldprt")
        spy.assert_not_called()

    def test_success_message_contains_name(self, tmp_path):
        f = tmp_path / "body.sldprt"
        f.write_text("")
        _setup_asm()
        result = server.sw_add_component(str(f))
        assert "body.sldprt" in result

    def test_position_in_result(self, tmp_path):
        f = tmp_path / "cap.sldprt"
        f.write_text("")
        _setup_asm()
        result = server.sw_add_component(str(f), x_mm=10.0, y_mm=20.0, z_mm=5.0)
        assert "10.0" in result
        assert "20.0" in result
        assert "5.0" in result

    def test_com_null_returns_error(self, tmp_path):
        f = tmp_path / "bad.sldprt"
        f.write_text("")

        class FakeAsm:
            Extension = MagicMock()

            def AddComponent4(self, *_):
                return None

        class FakeApp:
            ActiveDoc = FakeAsm()

        server.swApp = FakeApp()
        result = server.sw_add_component(str(f))
        assert "Не вдалось" in result


# ─── sw_add_mate ───────────────────────────────────────────────

class TestSwAddMate:
    def _setup_mate(self, mate_result=MagicMock()):
        asm = MagicMock()
        asm.FeatureManager.InsertMate5.return_value = mate_result

        class FakeApp:
            ActiveDoc = asm

        server.swApp = FakeApp()
        return asm

    def test_unknown_type_returns_error(self):
        _setup_asm()
        result = server.sw_add_mate("flux", "face1", "face2")
        assert "Невідомий тип" in result

    def test_valid_type_coincident(self):
        asm = self._setup_mate()
        result = server.sw_add_mate("coincident", "Body-1@asm", "Cap-1@asm")
        assert "coincident" in result

    def test_valid_type_concentric(self):
        asm = self._setup_mate()
        result = server.sw_add_mate("concentric", "A", "B")
        assert "concentric" in result

    def test_null_mate_returns_error(self):
        asm = self._setup_mate(mate_result=None)
        result = server.sw_add_mate("parallel", "A", "B")
        assert "Не вдалось" in result

    def test_mate_mentions_both_entities(self):
        self._setup_mate()
        result = server.sw_add_mate("distance", "EntityA", "EntityB")
        assert "EntityA" in result
        assert "EntityB" in result

    def test_all_valid_types_accepted(self):
        for mtype in ("coincident", "concentric", "parallel", "perpendicular", "distance", "angle"):
            self._setup_mate()
            result = server.sw_add_mate(mtype, "A", "B")
            assert "Невідомий" not in result, f"Type '{mtype}' was rejected"


# ─── sw_list_components ────────────────────────────────────────

class TestSwListComponents:
    def test_empty_assembly(self):
        class FakeAsm:
            def GetComponents(self, _):
                return []

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


# ─── sw_save_assembly ──────────────────────────────────────────

class TestSwSaveAssembly:
    def test_save_calls_save_as3(self, mocker):
        asm = MagicMock()

        class FakeApp:
            ActiveDoc = asm

        server.swApp = FakeApp()
        server.sw_save_assembly(r"C:\work\drever.sldasm")
        asm.SaveAs3.assert_called_once_with(r"C:\work\drever.sldasm", 0, 2)

    def test_result_contains_path(self, mocker):
        asm = MagicMock()

        class FakeApp:
            ActiveDoc = asm

        server.swApp = FakeApp()
        result = server.sw_save_assembly(r"C:\work\drever.sldasm")
        assert "drever.sldasm" in result
