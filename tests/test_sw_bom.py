"""Тести для sw_get_bom."""
import os
import pytest
import server


def _make_comp(path):
    class Comp:
        Name2 = os.path.basename(path) if path else "unknown"
        def GetPathName(self_): return path
    return Comp()


def _setup_asm(comps=None, raises=False):
    class FakeDoc:
        def GetComponents(self_, top_level):
            if raises:
                raise Exception("not assembly")
            return comps

    class FakeApp:
        ActiveDoc = FakeDoc()

    server._sw = lambda: FakeApp()


class TestSwGetBom:
    def test_returns_message_when_not_assembly(self):
        _setup_asm(raises=True)
        result = server.sw_get_bom()
        assert "не збірка" in result.lower() or "порожня" in result.lower()

    def test_returns_message_when_no_components(self):
        _setup_asm(comps=None)
        result = server.sw_get_bom()
        assert "не знайдено" in result.lower()

    def test_returns_message_when_empty_list(self):
        _setup_asm(comps=[])
        result = server.sw_get_bom()
        assert "не знайдено" in result.lower()

    def test_lists_component_names(self):
        comps = [_make_comp(r"C:\work\bracket.sldprt")]
        _setup_asm(comps=comps)
        result = server.sw_get_bom()
        assert "bracket.sldprt" in result

    def test_counts_duplicate_components(self):
        comps = [
            _make_comp(r"C:\work\bolt.sldprt"),
            _make_comp(r"C:\work\bolt.sldprt"),
            _make_comp(r"C:\work\bolt.sldprt"),
        ]
        _setup_asm(comps=comps)
        result = server.sw_get_bom()
        assert "3" in result
        assert result.count("bolt.sldprt") == 1

    def test_multiple_unique_components(self):
        comps = [
            _make_comp(r"C:\work\bracket.sldprt"),
            _make_comp(r"C:\work\bolt.sldprt"),
            _make_comp(r"C:\work\bolt.sldprt"),
        ]
        _setup_asm(comps=comps)
        result = server.sw_get_bom()
        assert "bracket.sldprt" in result
        assert "bolt.sldprt" in result

    def test_total_line_shows_counts(self):
        comps = [
            _make_comp(r"C:\work\a.sldprt"),
            _make_comp(r"C:\work\b.sldprt"),
            _make_comp(r"C:\work\b.sldprt"),
        ]
        _setup_asm(comps=comps)
        result = server.sw_get_bom()
        assert "3" in result   # total components
        assert "2" in result   # unique

    def test_uses_name2_when_path_empty(self):
        comp = _make_comp("")
        comp.Name2 = "unnamed_part"
        _setup_asm(comps=[comp])
        result = server.sw_get_bom()
        assert "unnamed_part" in result
