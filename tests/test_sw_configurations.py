"""Тести для sw_list/add/switch/delete_configuration."""
import pytest
import server


def _setup_doc(config_names=None, active_name="Default", add_result=None,
               show_result=True, delete_result=True):
    class FakeConfig:
        Name = active_name

    class FakeConfigManager:
        ActiveConfiguration = FakeConfig()

    class FakeDoc:
        ConfigurationManager = FakeConfigManager()

        def GetConfigurationNames(self_):
            return config_names

        def AddConfiguration2(self_, name, desc, comment, opts, parent):
            return add_result

        def ShowConfiguration2(self_, name):
            return show_result

        def DeleteConfiguration(self_, name):
            return delete_result

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()


# ──────────────────────────────────────────────────────────────
# sw_list_configurations
# ──────────────────────────────────────────────────────────────

class TestSwListConfigurations:
    def test_returns_empty_message_when_no_configs(self):
        _setup_doc(config_names=None)
        result = server.sw_list_configurations()
        assert "немає" in result.lower()

    def test_lists_config_names(self):
        _setup_doc(config_names=["Default", "Lightweight"])
        result = server.sw_list_configurations()
        assert "Default" in result
        assert "Lightweight" in result

    def test_marks_active_config(self):
        _setup_doc(config_names=["Default", "Heavy"], active_name="Default")
        result = server.sw_list_configurations()
        lines = result.splitlines()
        active_line = next(l for l in lines if "Default" in l)
        assert "активна" in active_line

    def test_non_active_configs_not_marked(self):
        _setup_doc(config_names=["Default", "Heavy"], active_name="Default")
        result = server.sw_list_configurations()
        lines = result.splitlines()
        heavy_line = next(l for l in lines if "Heavy" in l)
        assert "активна" not in heavy_line


# ──────────────────────────────────────────────────────────────
# sw_add_configuration
# ──────────────────────────────────────────────────────────────

class TestSwAddConfiguration:
    def test_raises_when_add_returns_none(self):
        _setup_doc(add_result=None)
        with pytest.raises(RuntimeError, match="Lightweight"):
            server.sw_add_configuration("Lightweight")

    def test_result_contains_name(self, mocker):
        _setup_doc(add_result=mocker.MagicMock())
        result = server.sw_add_configuration("Lightweight")
        assert "Lightweight" in result

    def test_passes_128_options_flag(self, mocker):
        calls = []

        class FakeDoc:
            ConfigurationManager = mocker.MagicMock()
            def GetConfigurationNames(self_): return []
            def AddConfiguration2(self_, name, desc, comment, opts, parent):
                calls.append(opts)
                return mocker.MagicMock()

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        server.sw_add_configuration("Test")
        assert calls[0] == 128


# ──────────────────────────────────────────────────────────────
# sw_switch_configuration
# ──────────────────────────────────────────────────────────────

class TestSwSwitchConfiguration:
    def test_returns_not_found_when_show_fails(self):
        _setup_doc(show_result=False)
        result = server.sw_switch_configuration("Missing")
        assert "не знайдено" in result

    def test_result_contains_config_name_on_success(self):
        _setup_doc(show_result=True)
        result = server.sw_switch_configuration("Heavy")
        assert "Heavy" in result

    def test_result_mentions_activation(self):
        _setup_doc(show_result=True)
        result = server.sw_switch_configuration("Heavy")
        assert "активовано" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_delete_configuration
# ──────────────────────────────────────────────────────────────

class TestSwDeleteConfiguration:
    def test_returns_error_when_delete_fails(self):
        _setup_doc(delete_result=False)
        result = server.sw_delete_configuration("Default")
        assert "не вдалось" in result.lower()

    def test_result_contains_name_on_success(self):
        _setup_doc(delete_result=True)
        result = server.sw_delete_configuration("Lightweight")
        assert "Lightweight" in result

    def test_result_mentions_deletion(self):
        _setup_doc(delete_result=True)
        result = server.sw_delete_configuration("Old")
        assert "видалено" in result.lower()
