"""Тести для sw_simulation_setup, sw_simulation_run, sw_simulation_results."""
import pytest
import server


def _setup_app(cosmos=None):
    class FakeApp:
        def GetAddInObject(self_, prog_id):
            return cosmos

    server._sw = lambda: FakeApp()


# ──────────────────────────────────────────────────────────────
# sw_simulation_setup
# ──────────────────────────────────────────────────────────────

class TestSwSimulationSetup:
    def test_raises_when_addin_not_loaded(self):
        _setup_app(cosmos=None)
        with pytest.raises(RuntimeError, match="CosmosWorks"):
            server.sw_simulation_setup()

    def test_raises_when_create_study_returns_none(self, mocker):
        study_mgr = mocker.MagicMock()
        study_mgr.CreateNewStudy3.return_value = None
        cw_doc = mocker.MagicMock()
        cw_doc.StudyManager.return_value = study_mgr
        cosmos = mocker.MagicMock()
        cosmos.cwDoc.return_value = cw_doc
        _setup_app(cosmos=cosmos)

        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id): return cosmos

        server._sw = lambda: FakeApp()
        with pytest.raises(RuntimeError, match="дослідження"):
            server.sw_simulation_setup("Static 1")

    def test_result_contains_study_name(self, mocker):
        study = mocker.MagicMock()
        study_mgr = mocker.MagicMock()
        study_mgr.CreateNewStudy3.return_value = study
        cw_doc = mocker.MagicMock()
        cw_doc.StudyManager.return_value = study_mgr
        cosmos = mocker.MagicMock()
        cosmos.cwDoc.return_value = cw_doc

        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id): return cosmos

        server._sw = lambda: FakeApp()
        result = server.sw_simulation_setup("My Study")
        assert "My Study" in result

    def test_passes_static_type_0(self, mocker):
        study = mocker.MagicMock()
        study_mgr = mocker.MagicMock()
        study_mgr.CreateNewStudy3.return_value = study
        cw_doc = mocker.MagicMock()
        cw_doc.StudyManager.return_value = study_mgr
        cosmos = mocker.MagicMock()
        cosmos.cwDoc.return_value = cw_doc

        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id): return cosmos

        server._sw = lambda: FakeApp()
        server.sw_simulation_setup("Static 1")
        args = study_mgr.CreateNewStudy3.call_args[0]
        assert args[1] == 0  # study type = static


# ──────────────────────────────────────────────────────────────
# sw_simulation_run
# ──────────────────────────────────────────────────────────────

class TestSwSimulationRun:
    def _setup(self, mocker, study_name="Static 1", run_errors=None,
               study_exists=True):
        study = mocker.MagicMock()
        study.RunStudy.return_value = run_errors
        study_mgr = mocker.MagicMock()
        study_mgr.GetStudy.return_value = study if study_exists else None
        cw_doc = mocker.MagicMock()
        cw_doc.StudyManager.return_value = study_mgr
        cosmos = mocker.MagicMock()
        cosmos.cwDoc.return_value = cw_doc

        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id): return cosmos

        server._sw = lambda: FakeApp()
        return study

    def test_returns_not_found_when_study_missing(self, mocker):
        self._setup(mocker, study_exists=False)
        result = server.sw_simulation_run("Missing Study")
        assert "не знайдено" in result.lower()

    def test_calls_run_study(self, mocker):
        study = self._setup(mocker)
        server.sw_simulation_run()
        study.RunStudy.assert_called_once()

    def test_result_contains_study_name_on_success(self, mocker):
        self._setup(mocker, run_errors=None)
        result = server.sw_simulation_run("Static 1")
        assert "Static 1" in result

    def test_result_mentions_warnings_when_errors(self, mocker):
        self._setup(mocker, run_errors="some warnings")
        result = server.sw_simulation_run()
        assert "попередження" in result.lower() or "warning" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_simulation_results
# ──────────────────────────────────────────────────────────────

class TestSwSimulationResults:
    def _setup(self, mocker, stress=5e6, displacement=0.002, fos=3.0):
        stress_data = mocker.MagicMock()
        stress_data.GetMaxValue.return_value = stress

        disp_data = mocker.MagicMock()
        disp_data.GetMaxValue.return_value = displacement

        fos_data = mocker.MagicMock()
        fos_data.GetMinValue.return_value = fos

        results = mocker.MagicMock()
        results.GetResultData2.side_effect = [stress_data, disp_data, fos_data]

        study = mocker.MagicMock()
        study.Results.return_value = results

        study_mgr = mocker.MagicMock()
        study_mgr.GetStudy.return_value = study

        cw_doc = mocker.MagicMock()
        cw_doc.StudyManager.return_value = study_mgr

        cosmos = mocker.MagicMock()
        cosmos.cwDoc.return_value = cw_doc

        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id): return cosmos

        server._sw = lambda: FakeApp()

    def test_result_contains_stress_in_mpa(self, mocker):
        self._setup(mocker, stress=5e6)
        result = server.sw_simulation_results()
        assert "5.00" in result or "МПа" in result

    def test_result_contains_displacement_in_mm(self, mocker):
        self._setup(mocker, displacement=0.002)
        result = server.sw_simulation_results()
        assert "2.0" in result or "мм" in result

    def test_result_contains_fos(self, mocker):
        self._setup(mocker, fos=2.5)
        result = server.sw_simulation_results()
        assert "2.5" in result or "запас" in result.lower()

    def test_result_contains_study_name(self, mocker):
        self._setup(mocker)
        result = server.sw_simulation_results("My Analysis")
        assert "My Analysis" in result

    def test_raises_on_exception(self, mocker):
        class FakeApp:
            ActiveDoc = mocker.MagicMock()
            def GetAddInObject(self_, prog_id):
                raise Exception("COM error")

        server._sw = lambda: FakeApp()
        with pytest.raises(RuntimeError):
            server.sw_simulation_results()
