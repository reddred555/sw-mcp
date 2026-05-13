"""Тести для sw_suppress_feature, sw_unsuppress_feature, sw_list_features."""
import pytest
import server


def _make_feature(name, ftype="Boss-Extrude", suppressed=False):
    class Feature:
        _next = None
        Name = name

        @property
        def GetTypeName2(self):
            return ftype

        def IsSuppressed2(self, cfg, names):
            return suppressed

        def SetSuppression2(self, state, cfg, names):
            self._last_state = state

        @property
        def GetNextFeature(self):
            return self._next

    return Feature()


def _chain(*feats):
    for i in range(len(feats) - 1):
        feats[i]._next = feats[i + 1]
    return feats[0]


def _setup_doc(*features):
    class FakeDoc:
        @property
        def FirstFeature(self_):
            return features[0] if features else None

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()
    if len(features) > 1:
        _chain(*features)


# ──────────────────────────────────────────────────────────────
# sw_suppress_feature
# ──────────────────────────────────────────────────────────────

class TestSwSuppressFeature:
    def test_suppresses_matching_feature(self):
        feat = _make_feature("Hole1")
        _setup_doc(feat)
        result = server.sw_suppress_feature("Hole1")
        assert "Придушено" in result
        assert feat._last_state == 0

    def test_not_found(self):
        feat = _make_feature("Hole1")
        _setup_doc(feat)
        result = server.sw_suppress_feature("Nonexistent")
        assert "не знайдено" in result

    def test_matches_correct_feature_in_chain(self):
        f1 = _make_feature("Cut1")
        f2 = _make_feature("Bend1")
        _setup_doc(f1, f2)
        result = server.sw_suppress_feature("Bend1")
        assert "Придушено" in result
        assert f2._last_state == 0


# ──────────────────────────────────────────────────────────────
# sw_unsuppress_feature
# ──────────────────────────────────────────────────────────────

class TestSwUnsuppressFeature:
    def test_unsuppresses_matching_feature(self):
        feat = _make_feature("Hole1", suppressed=True)
        _setup_doc(feat)
        result = server.sw_unsuppress_feature("Hole1")
        assert "Активовано" in result
        assert feat._last_state == 1  # state=1 означає unsuppress

    def test_not_found(self):
        feat = _make_feature("Hole1")
        _setup_doc(feat)
        result = server.sw_unsuppress_feature("Missing")
        assert "не знайдено" in result

    def test_suppress_uses_state_0_not_1(self):
        """Suppress і unsuppress мають різні state-аргументи — перевіряємо їх не переплутали."""
        feat = _make_feature("F1")
        _setup_doc(feat)
        server.sw_suppress_feature("F1")
        suppress_state = feat._last_state

        feat2 = _make_feature("F1")
        _setup_doc(feat2)
        server.sw_unsuppress_feature("F1")
        unsuppress_state = feat2._last_state

        assert suppress_state == 0
        assert unsuppress_state == 1
        assert suppress_state != unsuppress_state


# ──────────────────────────────────────────────────────────────
# sw_list_features
# ──────────────────────────────────────────────────────────────

class TestSwListFeatures:
    def test_no_features(self):
        class FakeDoc:
            FirstFeature = None

        class FakeApp:
            ActiveDoc = FakeDoc()

        server._sw = lambda: FakeApp()
        result = server.sw_list_features()
        assert result == "Немає features."

    def test_lists_feature_names_and_types(self):
        f1 = _make_feature("Extrude1", ftype="Boss-Extrude")
        f2 = _make_feature("Cut1", ftype="Cut-Extrude")
        _setup_doc(f1, f2)
        result = server.sw_list_features()
        assert "Extrude1" in result
        assert "Boss-Extrude" in result
        assert "Cut1" in result
        assert "Cut-Extrude" in result

    def test_suppressed_feature_marked(self):
        feat = _make_feature("Hidden", suppressed=True)
        _setup_doc(feat)
        result = server.sw_list_features()
        assert "[придушено]" in result

    def test_active_feature_not_marked(self):
        feat = _make_feature("Visible", suppressed=False)
        _setup_doc(feat)
        result = server.sw_list_features()
        assert "[придушено]" not in result
