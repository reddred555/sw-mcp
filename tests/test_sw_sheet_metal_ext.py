"""Тести для sw_edge_flange та sw_flat_pattern."""
import math
import pytest
import server


# ──────────────────────────────────────────────────────────────
# sw_edge_flange
# ──────────────────────────────────────────────────────────────

class TestSwEdgeFlange:
    def _setup_fm(self, feat_return=None, raises=False):
        class FakeFM:
            def InsertSheetMetalEdgeFlange(self_, *args):
                if raises:
                    raise Exception("COM error")
                return feat_return

        class FakeDoc:
            FeatureManager = FakeFM()

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()

    def test_raises_when_com_raises(self):
        self._setup_fm(raises=True)
        with pytest.raises(RuntimeError, match="Edge Flange"):
            server.sw_edge_flange(10.0)

    def test_raises_when_feat_is_none(self):
        self._setup_fm(feat_return=None)
        with pytest.raises(RuntimeError, match="Edge Flange"):
            server.sw_edge_flange(10.0)

    def test_result_contains_height(self, mocker):
        self._setup_fm(feat_return=mocker.MagicMock())
        result = server.sw_edge_flange(15.0)
        assert "15" in result

    def test_result_contains_angle(self, mocker):
        self._setup_fm(feat_return=mocker.MagicMock())
        result = server.sw_edge_flange(10.0, angle_deg=45.0)
        assert "45" in result

    def test_result_contains_radius(self, mocker):
        self._setup_fm(feat_return=mocker.MagicMock())
        result = server.sw_edge_flange(10.0, bend_radius_mm=2.0)
        assert "2" in result


# ──────────────────────────────────────────────────────────────
# sw_flat_pattern
# ──────────────────────────────────────────────────────────────

def _make_feature(ftype, suppressed_calls=None):
    calls = suppressed_calls if suppressed_calls is not None else []

    class Feat:
        _next = None

        def GetTypeName2(self_):
            return ftype

        def SetSuppression2(self_, state, cfg, names):
            calls.append(state)

        def GetNextFeature(self_):
            return self_._next

    return Feat(), calls


def _setup_flat(features):
    class FakeDoc:
        def FirstFeature(self_):
            return features[0] if features else None

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()
    for i in range(len(features) - 1):
        features[i]._next = features[i + 1]


class TestSwFlatPattern:
    def test_returns_not_found_when_no_flat_pattern(self):
        f, _ = _make_feature("Boss-Extrude")
        _setup_flat([f])
        result = server.sw_flat_pattern(show=True)
        assert "не знайдено" in result.lower()

    def test_show_true_calls_suppression_1(self):
        f, calls = _make_feature("FlatPattern")
        _setup_flat([f])
        server.sw_flat_pattern(show=True)
        assert calls == [1]

    def test_show_false_calls_suppression_0(self):
        f, calls = _make_feature("FlatPattern")
        _setup_flat([f])
        server.sw_flat_pattern(show=False)
        assert calls == [0]

    def test_also_finds_flat_bend_type(self):
        f, calls = _make_feature("FlatBend")
        _setup_flat([f])
        server.sw_flat_pattern(show=True)
        assert calls == [1]

    def test_result_mentions_show_state(self):
        f, _ = _make_feature("FlatPattern")
        _setup_flat([f])
        result = server.sw_flat_pattern(show=True)
        assert "показана" in result

    def test_result_mentions_hide_state(self):
        f, _ = _make_feature("FlatPattern")
        _setup_flat([f])
        result = server.sw_flat_pattern(show=False)
        assert "прихована" in result

    def test_skips_non_flat_features(self):
        other, _ = _make_feature("Boss-Extrude")
        flat, calls = _make_feature("FlatPattern")
        _setup_flat([other, flat])
        server.sw_flat_pattern(show=True)
        assert calls == [1]
