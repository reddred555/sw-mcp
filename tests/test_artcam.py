"""Тести для artcam_create_macro та artcam_post_wdmax."""
import os
import pytest
import server


# ──────────────────────────────────────────────────────────────
# artcam_post_wdmax
# ──────────────────────────────────────────────────────────────

class TestArtcamPostWdmax:
    def test_output_filename_convention(self, tmp_path):
        nc = tmp_path / "part.nc"
        nc.write_text("G0 X0 Y0\n")
        result = server.artcam_post_wdmax(str(nc))
        assert "_wdmax.nc" in result
        assert result.endswith("part_wdmax.nc")

    def test_header_lines_present(self, tmp_path):
        nc = tmp_path / "part.nc"
        nc.write_text("G0 X0\n")
        out_path = str(nc).replace(".nc", "_wdmax.nc")
        server.artcam_post_wdmax(str(nc))
        content = open(out_path).read()
        assert "G21 G90 G17" in content
        assert "G94" in content
        assert "; STUKACH MFG" in content
        assert "; WDMAX CNC" in content

    def test_source_filename_in_header(self, tmp_path):
        nc = tmp_path / "my_part.nc"
        nc.write_text("")
        server.artcam_post_wdmax(str(nc))
        out_path = str(nc).replace(".nc", "_wdmax.nc")
        content = open(out_path).read()
        assert str(nc) in content

    def test_original_content_preserved(self, tmp_path):
        nc = tmp_path / "part.nc"
        body = "G1 X10 Y20 F500\nM30\n"
        nc.write_text(body)
        out_path = str(nc).replace(".nc", "_wdmax.nc")
        server.artcam_post_wdmax(str(nc))
        content = open(out_path).read()
        assert content.endswith(body)

    def test_header_comes_before_content(self, tmp_path):
        nc = tmp_path / "part.nc"
        nc.write_text("M30\n")
        out_path = str(nc).replace(".nc", "_wdmax.nc")
        server.artcam_post_wdmax(str(nc))
        content = open(out_path).read()
        header_end = content.index("G94") + len("G94")
        m30_pos = content.index("M30")
        assert header_end < m30_pos


# ──────────────────────────────────────────────────────────────
# artcam_create_macro
# ──────────────────────────────────────────────────────────────

class TestArtcamCreateMacro:
    def _run(self, tmp_path, strategy="profile", **kwargs):
        art = str(tmp_path / "part.art")
        # Підміняємо ARTCAM_MACROS на tmp_path, щоб не писати в C:\
        original = server.ARTCAM_MACROS
        server.ARTCAM_MACROS = str(tmp_path)
        try:
            result = server.artcam_create_macro(art, strategy=strategy, **kwargs)
        finally:
            server.ARTCAM_MACROS = original
        macro_path = os.path.join(str(tmp_path), "toolpath.bas")
        return result, open(macro_path).read()

    def test_profile_strategy(self, tmp_path):
        _, macro = self._run(tmp_path, strategy="profile")
        assert "AddProfileToolpath" in macro

    def test_pocket_strategy(self, tmp_path):
        _, macro = self._run(tmp_path, strategy="pocket")
        assert "AddPocketToolpath" in macro

    def test_contour_strategy(self, tmp_path):
        _, macro = self._run(tmp_path, strategy="contour")
        assert "AddContourToolpath" in macro

    def test_unknown_strategy_falls_back_to_profile(self, tmp_path):
        _, macro = self._run(tmp_path, strategy="spiral")
        assert "AddProfileToolpath" in macro

    def test_default_output_nc_derived_from_art(self, tmp_path):
        result, _ = self._run(tmp_path)
        art_path = str(tmp_path / "part.art")
        expected_nc = art_path.replace(".art", ".nc")
        assert expected_nc in result

    def test_custom_output_nc(self, tmp_path):
        art = str(tmp_path / "part.art")
        nc = str(tmp_path / "custom_output.nc")
        original = server.ARTCAM_MACROS
        server.ARTCAM_MACROS = str(tmp_path)
        try:
            result = server.artcam_create_macro(art, output_nc=nc)
        finally:
            server.ARTCAM_MACROS = original
        assert "custom_output.nc" in result

    def test_tool_parameters_in_macro(self, tmp_path):
        _, macro = self._run(
            tmp_path,
            tool_diameter_mm=8.0,
            feed_rate=2000.0,
            spindle_rpm=20000,
            pass_depth_mm=3.0,
            depth_mm=15.0,
        )
        assert "8.0" in macro
        assert "2000.0" in macro
        assert "20000" in macro
        assert "3.0" in macro
        assert "15.0" in macro

    def test_plunge_rate_is_half_feed_rate(self, tmp_path):
        _, macro = self._run(tmp_path, feed_rate=1000.0)
        assert "500.0" in macro  # plunge = feed * 0.5

    def test_macro_file_created(self, tmp_path):
        self._run(tmp_path)
        assert os.path.exists(os.path.join(str(tmp_path), "toolpath.bas"))
