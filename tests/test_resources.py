"""Тести для MCP resources (docs://drever/spec та ін.)."""
import os
import pytest
import server


class TestDreverSpec:
    def test_returns_file_contents(self, tmp_path, monkeypatch):
        doc = tmp_path / "drever_ingeniering_v1.md"
        doc.write_text("# Drever spec\nContent here.", encoding="utf-8")
        monkeypatch.setattr(server, "DOCS_DIR", str(tmp_path))
        result = server.drever_spec()
        assert "Drever spec" in result
        assert "Content here." in result

    def test_full_content_returned(self, tmp_path, monkeypatch):
        content = "line1\nline2\nline3\n"
        doc = tmp_path / "drever_ingeniering_v1.md"
        doc.write_text(content, encoding="utf-8")
        monkeypatch.setattr(server, "DOCS_DIR", str(tmp_path))
        assert server.drever_spec() == content

    def test_unicode_content(self, tmp_path, monkeypatch):
        doc = tmp_path / "drever_ingeniering_v1.md"
        doc.write_text("Технічний звіт: ✓ OK", encoding="utf-8")
        monkeypatch.setattr(server, "DOCS_DIR", str(tmp_path))
        result = server.drever_spec()
        assert "Технічний звіт" in result
        assert "✓ OK" in result

    def test_raises_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "DOCS_DIR", str(tmp_path))
        with pytest.raises(FileNotFoundError):
            server.drever_spec()

    def test_reads_from_docs_dir(self, tmp_path, monkeypatch):
        other = tmp_path / "other"
        other.mkdir()
        doc = tmp_path / "drever_ingeniering_v1.md"
        doc.write_text("correct", encoding="utf-8")
        monkeypatch.setattr(server, "DOCS_DIR", str(tmp_path))
        assert server.drever_spec() == "correct"
