"""Тести для інструментів ескізу: sw_sketch_start/line/circle/arc/finish."""
import math
import pytest
import server


class FakeSketchManager:
    def __init__(self):
        self.sketches = []
        self.lines = []
        self.circles = []
        self.arcs = []

    def InsertSketch(self, close):
        self.sketches.append(close)

    def CreateLine(self, x1, y1, z1, x2, y2, z2):
        self.lines.append((x1, y1, z1, x2, y2, z2))

    def CreateCircle(self, cx, cy, cz, px, py, pz):
        self.circles.append((cx, cy, cz, px, py, pz))

    def CreateArc(self, cx, cy, cz, sx, sy, sz, ex, ey, ez, direction):
        self.arcs.append((cx, cy, cz, sx, sy, sz, ex, ey, ez, direction))


class FakeExtension:
    def __init__(self):
        self.selections = []

    def SelectByID2(self, name, etype, x, y, z, append, mark, callout, selopt):
        self.selections.append((name, etype))


def _setup_doc():
    sm = FakeSketchManager()
    ext = FakeExtension()

    class FakeDoc:
        SketchManager = sm
        Extension = ext

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()
    return sm, ext


# ──────────────────────────────────────────────────────────────
# sw_sketch_start
# ──────────────────────────────────────────────────────────────

class TestSwSketchStart:
    def test_selects_correct_plane(self):
        sm, ext = _setup_doc()
        server.sw_sketch_start("Top Plane")
        assert any(name == "Top Plane" and etype == "PLANE"
                   for name, etype in ext.selections)

    def test_default_plane_is_front(self):
        sm, ext = _setup_doc()
        server.sw_sketch_start()
        assert ext.selections[0][0] == "Front Plane"

    def test_calls_insert_sketch(self):
        sm, _ = _setup_doc()
        server.sw_sketch_start()
        assert len(sm.sketches) == 1

    def test_result_contains_plane_name(self):
        _setup_doc()
        result = server.sw_sketch_start("Right Plane")
        assert "Right Plane" in result


# ──────────────────────────────────────────────────────────────
# sw_sketch_line
# ──────────────────────────────────────────────────────────────

class TestSwSketchLine:
    def test_converts_mm_to_m(self):
        sm, _ = _setup_doc()
        server.sw_sketch_line(10.0, 20.0, 30.0, 40.0)
        x1, y1, z1, x2, y2, z2 = sm.lines[0]
        assert x1 == pytest.approx(0.010)
        assert y1 == pytest.approx(0.020)
        assert x2 == pytest.approx(0.030)
        assert y2 == pytest.approx(0.040)

    def test_z_is_zero(self):
        sm, _ = _setup_doc()
        server.sw_sketch_line(0, 0, 10, 10)
        _, _, z1, _, _, z2 = sm.lines[0]
        assert z1 == 0
        assert z2 == 0

    def test_result_contains_coords(self):
        _setup_doc()
        result = server.sw_sketch_line(5.0, 10.0, 15.0, 20.0)
        assert "5" in result and "15" in result


# ──────────────────────────────────────────────────────────────
# sw_sketch_circle
# ──────────────────────────────────────────────────────────────

class TestSwSketchCircle:
    def test_center_coords_converted(self):
        sm, _ = _setup_doc()
        server.sw_sketch_circle(20.0, 30.0, 10.0)
        cx, cy, cz, *_ = sm.circles[0]
        assert cx == pytest.approx(0.020)
        assert cy == pytest.approx(0.030)

    def test_radius_point_is_center_plus_radius_on_x(self):
        sm, _ = _setup_doc()
        server.sw_sketch_circle(0.0, 0.0, 15.0)
        cx, cy, _, px, py, _ = sm.circles[0]
        assert px == pytest.approx(cx + 0.015)
        assert py == pytest.approx(cy)

    def test_result_contains_radius(self):
        _setup_doc()
        result = server.sw_sketch_circle(0, 0, 25.0)
        assert "25" in result


# ──────────────────────────────────────────────────────────────
# sw_sketch_arc
# ──────────────────────────────────────────────────────────────

class TestSwSketchArc:
    def test_start_point_at_0_deg(self):
        sm, _ = _setup_doc()
        server.sw_sketch_arc(0.0, 0.0, 10.0, 0.0, 90.0)
        cx, cy, _, sx, sy, *_ = sm.arcs[0]
        assert sx == pytest.approx(cx + 0.010, abs=1e-9)
        assert sy == pytest.approx(cy, abs=1e-9)

    def test_end_point_at_90_deg(self):
        sm, _ = _setup_doc()
        server.sw_sketch_arc(0.0, 0.0, 10.0, 0.0, 90.0)
        cx, cy, _, _, _, _, ex, ey, *_ = sm.arcs[0]
        assert ex == pytest.approx(cx, abs=1e-9)
        assert ey == pytest.approx(cy + 0.010, abs=1e-9)

    def test_direction_is_ccw(self):
        sm, _ = _setup_doc()
        server.sw_sketch_arc(0.0, 0.0, 5.0, 0.0, 180.0)
        *_, direction = sm.arcs[0]
        assert direction == 1

    def test_result_contains_angles(self):
        _setup_doc()
        result = server.sw_sketch_arc(0, 0, 10, 45.0, 135.0)
        assert "45" in result and "135" in result


# ──────────────────────────────────────────────────────────────
# sw_sketch_finish
# ──────────────────────────────────────────────────────────────

class TestSwSketchFinish:
    def test_calls_insert_sketch(self):
        sm, _ = _setup_doc()
        server.sw_sketch_finish()
        assert len(sm.sketches) == 1

    def test_result_mentions_finish(self):
        _setup_doc()
        result = server.sw_sketch_finish()
        assert "завершено" in result.lower() or "ескіз" in result.lower()
