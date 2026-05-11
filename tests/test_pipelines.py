"""Тести для pipeline_laser, pipeline_print, pipeline_milling."""
import os
import pytest
from unittest.mock import patch, MagicMock
import server


def _mock_sub_tools(mocker):
    """Підміняє всі SW/ArtCAM-функції в межах server модуля."""
    mocks = {}
    for name in [
        "sw_new_part", "sw_set_material", "sw_base_flange",
        "sw_save", "sw_export_dxf", "sw_export_stl", "sw_export_3mf",
        "artcam_open", "artcam_create_macro",
    ]:
        mocks[name] = mocker.patch(f"server.{name}", return_value="ok")
    return mocks


# ──────────────────────────────────────────────────────────────
# pipeline_laser
# ──────────────────────────────────────────────────────────────

class TestPipelineLaser:
    def test_output_filenames_contain_dimensions(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_laser(100.0, 200.0, 3.0)
        assert "laser_100x200x3" in result

    def test_int_truncation_in_name(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_laser(100.9, 200.1, 3.7)
        assert "laser_100x200x3" in result

    def test_dxf_extension_in_result(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_laser(50.0, 50.0, 2.0)
        assert ".dxf" in result

    def test_calls_export_dxf(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_laser(100.0, 100.0, 3.0)
        mocks["sw_export_dxf"].assert_called_once()

    def test_custom_material_passed_to_set_material(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_laser(100.0, 100.0, 3.0, material="AISI 304")
        mocks["sw_set_material"].assert_called_once_with("AISI 304")

    def test_default_material_is_plain_carbon_steel(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_laser(100.0, 100.0, 3.0)
        mocks["sw_set_material"].assert_called_once_with("Plain Carbon Steel")


# ──────────────────────────────────────────────────────────────
# pipeline_print
# ──────────────────────────────────────────────────────────────

class TestPipelinePrint:
    def test_stl_format_calls_export_stl(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_print(100.0, 100.0, 10.0, format="stl")
        mocks["sw_export_stl"].assert_called_once()
        mocks["sw_export_3mf"].assert_not_called()

    def test_3mf_format_calls_export_3mf(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_print(100.0, 100.0, 10.0, format="3mf")
        mocks["sw_export_3mf"].assert_called_once()
        mocks["sw_export_stl"].assert_not_called()

    def test_output_filename_has_correct_extension(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_print(100.0, 100.0, 10.0, format="stl")
        call_args = mocks["sw_export_stl"].call_args[0][0]
        assert call_args.endswith(".stl")

    def test_3mf_output_filename(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_print(100.0, 100.0, 10.0, format="3mf")
        call_args = mocks["sw_export_3mf"].call_args[0][0]
        assert call_args.endswith(".3mf")

    def test_name_contains_dimensions(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_print(80.0, 60.0, 20.0)
        assert "print_80x60x20" in result


# ──────────────────────────────────────────────────────────────
# pipeline_milling
# ──────────────────────────────────────────────────────────────

class TestPipelineMilling:
    def test_artcam_open_called_with_dxf(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_milling(100.0, 100.0, 10.0)
        call_args = mocks["artcam_open"].call_args[0][0]
        assert call_args.endswith(".dxf")

    def test_macro_created_with_correct_strategy(self, mocker):
        mocks = _mock_sub_tools(mocker)
        server.pipeline_milling(100.0, 100.0, 10.0, strategy="pocket")
        call_kwargs = mocks["artcam_create_macro"].call_args
        assert "pocket" in call_kwargs[0] or call_kwargs[1].get("strategy") == "pocket"

    def test_result_mentions_wdmax_followup(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_milling(100.0, 100.0, 10.0)
        assert "artcam_post_wdmax" in result

    def test_name_contains_dimensions(self, mocker):
        _mock_sub_tools(mocker)
        result = server.pipeline_milling(120.0, 80.0, 15.0)
        assert "mill_120x80x15" in result
