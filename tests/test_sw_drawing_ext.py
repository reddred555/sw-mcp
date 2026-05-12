"""Тести для sw_add_smart_dimension."""
import pytest
import server


def _setup_doc(dim_return=None, raises=False):
    class FakeDoc:
        def AddSmartDimension(self_):
            if raises:
                raise Exception("COM error")
            return dim_return

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()


class TestSwAddSmartDimension:
    def test_raises_when_dim_is_none(self):
        _setup_doc(dim_return=None)
        with pytest.raises(RuntimeError, match="розмір"):
            server.sw_add_smart_dimension()

    def test_raises_on_com_exception(self):
        _setup_doc(raises=True)
        with pytest.raises(Exception):
            server.sw_add_smart_dimension()

    def test_returns_success_message(self, mocker):
        _setup_doc(dim_return=mocker.MagicMock())
        result = server.sw_add_smart_dimension()
        assert "Розмір" in result

    def test_calls_add_smart_dimension(self, mocker):
        calls = []

        class FakeDoc:
            def AddSmartDimension(self_):
                calls.append(True)
                return mocker.MagicMock()

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        server.sw_add_smart_dimension()
        assert len(calls) == 1
