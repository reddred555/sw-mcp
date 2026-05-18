"""Тести для sw_sweep та sw_loft."""
import pytest
import server


def _setup_doc(fm):
    class FakeDoc:
        FeatureManager = fm

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()


# ──────────────────────────────────────────────────────────────
# sw_sweep
# ──────────────────────────────────────────────────────────────

class TestSwSweep:
    def test_calls_insert_sweep2(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertSweep2.return_value = mocker.MagicMock()
        _setup_doc(fm)
        server.sw_sweep()
        fm.InsertSweep2.assert_called_once()

    def test_first_arg_is_solid_true(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertSweep2.return_value = mocker.MagicMock()
        _setup_doc(fm)
        server.sw_sweep()
        assert fm.InsertSweep2.call_args[0][0] is True

    def test_raises_when_insert_returns_none(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertSweep2.return_value = None
        _setup_doc(fm)
        with pytest.raises(RuntimeError, match="Sweep"):
            server.sw_sweep()

    def test_returns_success_message(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertSweep2.return_value = mocker.MagicMock()
        _setup_doc(fm)
        result = server.sw_sweep()
        assert "виконано" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_loft
# ──────────────────────────────────────────────────────────────

class TestSwLoft:
    def test_succeeds_with_insert_lofted_boss(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertLoftedBoss.return_value = mocker.MagicMock()
        _setup_doc(fm)
        result = server.sw_loft()
        assert "виконано" in result.lower()

    def test_falls_back_to_insert_lofted_boss2(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertLoftedBoss.side_effect = Exception("v1 fail")
        fm.InsertLoftedBoss2.return_value = mocker.MagicMock()
        _setup_doc(fm)
        result = server.sw_loft()
        assert "виконано" in result.lower()
        fm.InsertLoftedBoss2.assert_called_once()

    def test_raises_when_both_methods_fail(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertLoftedBoss.side_effect = Exception("v1 fail")
        fm.InsertLoftedBoss2.side_effect = Exception("v2 fail")
        _setup_doc(fm)
        with pytest.raises(RuntimeError, match="Loft"):
            server.sw_loft()

    def test_raises_when_first_returns_none_and_second_fails(self, mocker):
        fm = mocker.MagicMock()
        fm.InsertLoftedBoss.return_value = None
        fm.InsertLoftedBoss2.side_effect = Exception("v2 fail")
        _setup_doc(fm)
        with pytest.raises(RuntimeError):
            server.sw_loft()
