"""Тести для sw_new_part — логіка вибору шаблону."""
import pytest
from unittest.mock import patch, MagicMock
import server


class TestSwNewPart:
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
                server.sw_new_part()

    def test_uses_preference_path_when_valid(self):
        app = self._setup_app(preference_path=r"C:\templates\Part.PRTDOT")
        with patch("os.path.exists", return_value=True):
            with patch.object(app, "NewDocument") as mock_new:
                server.sw_new_part()
                mock_new.assert_called_once_with(r"C:\templates\Part.PRTDOT", 0, 0, 0)

    def test_falls_back_to_candidate_when_preference_missing(self):
        app = self._setup_app(preference_path="")
        candidate = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Part.PRTDOT"

        def exists_side_effect(path):
            return path == candidate

        with patch("os.path.exists", side_effect=exists_side_effect):
            with patch.object(app, "NewDocument") as mock_new:
                result = server.sw_new_part()
                mock_new.assert_called_once_with(candidate, 0, 0, 0)
                assert "Нова деталь" in result

    def test_preference_path_ignored_when_file_not_exist(self):
        app = self._setup_app(preference_path=r"C:\missing\Part.PRTDOT")
        candidate = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Part.PRTDOT"

        def exists_side_effect(path):
            return path == candidate

        with patch("os.path.exists", side_effect=exists_side_effect):
            with patch.object(app, "NewDocument") as mock_new:
                server.sw_new_part()
                mock_new.assert_called_once_with(candidate, 0, 0, 0)
