"""Тести для analyze_dxf — діагностика DXF-файлів."""
import os
import textwrap
import pytest
import server


def _write_dxf(tmp_path, entities_body: str) -> str:
    """Записати мінімальний ASCII DXF з довільним вмістом ENTITIES."""
    content = textwrap.dedent(f"""\
        0
        SECTION
        2
        ENTITIES
        {entities_body.strip()}
        0
        ENDSEC
        0
        EOF
    """)
    path = str(tmp_path / "test.dxf")
    with open(path, "w") as f:
        f.write(content)
    return path


CIRCLE_BODY = """\
0
CIRCLE
8
0
10
50.0
20
75.0
30
0.0
40
10.0"""

LINE_BODY = """\
0
LINE
8
0
10
0.0
20
0.0
30
0.0
11
100.0
21
200.0
31
0.0"""

ARC_BODY = """\
0
ARC
8
0
10
0.0
20
0.0
30
0.0
40
30.0
50
0.0
51
90.0"""


class TestAnalyzeDxfBasic:
    def test_missing_file_returns_error(self):
        result = server.analyze_dxf("/no/such/file.dxf")
        assert "не знайдено" in result

    def test_missing_file_includes_path(self):
        result = server.analyze_dxf("/no/such/file.dxf")
        assert "/no/such/file.dxf" in result

    def test_empty_entities_returns_warning(self, tmp_path):
        path = _write_dxf(tmp_path, "")
        result = server.analyze_dxf(path)
        assert "не знайдена або порожня" in result or "не виявлена" in result

    def test_filename_in_output(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        assert "test.dxf" in result


class TestAnalyzeDxfCircle:
    def test_circle_counted(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        assert "CIRCLE: 1" in result

    def test_circle_radius_in_output(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        assert "R=10.000" in result

    def test_circle_center_x_in_output(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        assert "cx=50.000" in result

    def test_circle_center_y_in_output(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        assert "cy=75.000" in result

    def test_bounding_box_includes_circle_radius(self, tmp_path):
        path = _write_dxf(tmp_path, CIRCLE_BODY)
        result = server.analyze_dxf(path)
        # bounding box width = 2*R = 20
        assert "20.000" in result

    def test_multiple_circles_counted(self, tmp_path):
        body = CIRCLE_BODY + "\n" + CIRCLE_BODY.replace("50.0\n20\n75.0", "150.0\n20\n175.0")
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "CIRCLE: 2" in result

    def test_multiple_circles_all_listed(self, tmp_path):
        body = CIRCLE_BODY + "\n" + """\
0
CIRCLE
8
0
10
200.0
20
300.0
30
0.0
40
5.0"""
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "R=10.000" in result
        assert "R=5.000" in result


class TestAnalyzeDxfLine:
    def test_line_counted(self, tmp_path):
        path = _write_dxf(tmp_path, LINE_BODY)
        result = server.analyze_dxf(path)
        assert "LINE: 1" in result

    def test_line_contributes_to_bounding_box(self, tmp_path):
        path = _write_dxf(tmp_path, LINE_BODY)
        result = server.analyze_dxf(path)
        # width = 100, height = 200
        assert "100.000" in result
        assert "200.000" in result


class TestAnalyzeDxfArc:
    def test_arc_counted(self, tmp_path):
        path = _write_dxf(tmp_path, ARC_BODY)
        result = server.analyze_dxf(path)
        assert "ARC: 1" in result

    def test_arc_contributes_to_bounding_box(self, tmp_path):
        path = _write_dxf(tmp_path, ARC_BODY)
        result = server.analyze_dxf(path)
        # R=30 → bbox at least 60×60
        assert "60.000" in result


class TestAnalyzeDxfMixed:
    def test_total_count(self, tmp_path):
        body = CIRCLE_BODY + "\n" + LINE_BODY + "\n" + ARC_BODY
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "Всього примітивів: 3" in result

    def test_all_types_present(self, tmp_path):
        body = CIRCLE_BODY + "\n" + LINE_BODY + "\n" + ARC_BODY
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "CIRCLE: 1" in result
        assert "LINE: 1" in result
        assert "ARC: 1" in result

    def test_gabarity_section_present(self, tmp_path):
        body = CIRCLE_BODY + "\n" + LINE_BODY
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "Габарит" in result

    def test_kola_section_present(self, tmp_path):
        body = CIRCLE_BODY + "\n" + LINE_BODY
        path = _write_dxf(tmp_path, body)
        result = server.analyze_dxf(path)
        assert "Кола" in result
