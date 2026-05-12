"""Тести для sw_set_property, sw_get_property, sw_list_properties."""
import pytest
import server


class FakeMgr:
    def __init__(self, props=None):
        self._props = props or {}
        self.sets = {}

    def Set2(self, name, type_id, value):
        self.sets[name] = (type_id, value)

    def Get5(self, name, resolve):
        if name in self._props:
            v = self._props[name]
            return (1, v, v, True)
        return (0, "", "", False)

    def GetNames(self):
        return list(self._props.keys()) if self._props else None


def _setup(props=None):
    mgr = FakeMgr(props)

    class FakeExtension:
        def CustomPropertyManager(self_, config):
            return mgr

    class FakeDoc:
        Extension = FakeExtension()

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()
    return mgr


# ──────────────────────────────────────────────────────────────
# sw_set_property
# ──────────────────────────────────────────────────────────────

class TestSwSetProperty:
    def test_calls_set2_with_text_type(self):
        mgr = _setup()
        server.sw_set_property("PartNo", "SKU-001")
        assert "PartNo" in mgr.sets
        assert mgr.sets["PartNo"] == (30, "SKU-001")

    def test_result_contains_name_and_value(self):
        _setup()
        result = server.sw_set_property("Description", "Bracket")
        assert "Description" in result
        assert "Bracket" in result

    def test_passes_config_argument(self, mocker):
        mgr = _setup()
        configs_seen = []

        class FakeExt:
            def CustomPropertyManager(self_, config):
                configs_seen.append(config)
                return mgr

        class FakeDoc:
            Extension = FakeExt()

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        server.sw_set_property("Rev", "A", config="Config1")
        assert "Config1" in configs_seen


# ──────────────────────────────────────────────────────────────
# sw_get_property
# ──────────────────────────────────────────────────────────────

class TestSwGetProperty:
    def test_returns_not_found_when_result_is_none(self, mocker):
        mgr = mocker.MagicMock()
        mgr.Get5.return_value = None

        class FakeExt:
            def CustomPropertyManager(self_, config):
                return mgr

        class FakeDoc:
            Extension = FakeExt()

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        result = server.sw_get_property("Missing")
        assert "не знайдена" in result

    def test_returns_not_found_when_ret_val_is_0(self):
        _setup(props={})
        result = server.sw_get_property("Nonexistent")
        assert "не знайдена" in result

    def test_returns_value_when_found(self):
        _setup(props={"PartNo": "SKU-001"})
        result = server.sw_get_property("PartNo")
        assert "PartNo" in result
        assert "SKU-001" in result

    def test_returns_resolved_value(self):
        _setup(props={"Mass": "42g"})
        result = server.sw_get_property("Mass")
        assert "42g" in result


# ──────────────────────────────────────────────────────────────
# sw_list_properties
# ──────────────────────────────────────────────────────────────

class TestSwListProperties:
    def test_returns_empty_message_when_no_names(self):
        _setup(props={})
        result = server.sw_list_properties()
        assert "немає" in result.lower()

    def test_lists_all_properties(self):
        _setup(props={"PartNo": "SKU-001", "Description": "Bracket"})
        result = server.sw_list_properties()
        assert "PartNo" in result
        assert "SKU-001" in result
        assert "Description" in result
        assert "Bracket" in result

    def test_each_property_on_separate_line(self):
        _setup(props={"A": "1", "B": "2"})
        result = server.sw_list_properties()
        assert result.count("\n") >= 1
