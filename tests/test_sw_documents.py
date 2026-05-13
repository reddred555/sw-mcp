"""Тести для функцій роботи з документами SolidWorks (з мок-об'єктами)."""
import pytest
import server


def _make_doc(title, path="", doc_type=1, is_active=False, unsaved=False):
    """Фабрика мок-документа."""
    _title = title
    _path = path
    _doc_type = doc_type
    _unsaved = unsaved

    class Doc:
        def GetTitle(self):
            return _title

        def GetPathName(self):
            return _path

        def GetType(self):
            return _doc_type

        def GetSaveFlag(self):
            return not _unsaved

    return Doc()


# ──────────────────────────────────────────────────────────────
# sw_list_documents
# ──────────────────────────────────────────────────────────────

class TestSwListDocuments:
    def _setup(self, docs, active=None):
        _docs = docs
        _active = active

        class FakeApp:
            def GetDocuments(self_):
                return _docs
            ActiveDoc = _active

        server._sw = lambda: FakeApp()

    def test_no_documents(self):
        self._setup([])
        result = server.sw_list_documents()
        assert result == "Немає відкритих документів."

    def test_lists_single_part(self):
        doc = _make_doc("plate.sldprt", path=r"C:\work\plate.sldprt", doc_type=1)
        self._setup([doc])
        result = server.sw_list_documents()
        assert "[Part]" in result
        assert "plate.sldprt" in result

    def test_doc_types(self):
        part = _make_doc("p.sldprt", doc_type=1)
        asm = _make_doc("a.sldasm", doc_type=2)
        drw = _make_doc("d.slddrw", doc_type=3)
        unk = _make_doc("x.file", doc_type=99)
        self._setup([part, asm, drw, unk])
        result = server.sw_list_documents()
        assert "[Part]" in result
        assert "[Assembly]" in result
        assert "[Drawing]" in result
        assert "[Unknown]" in result

    def test_active_document_marked(self):
        doc = _make_doc("active.sldprt", path=r"C:\work\active.sldprt")
        self._setup([doc], active=doc)
        result = server.sw_list_documents()
        assert "← активний" in result

    def test_unsaved_document_marked(self):
        doc = _make_doc("dirty.sldprt", unsaved=True)
        self._setup([doc])
        result = server.sw_list_documents()
        assert "[не збережено]" in result

    def test_duplicate_suppression(self):
        doc1 = _make_doc("same.sldprt", path=r"C:\work\same.sldprt")
        doc2 = _make_doc("same.sldprt", path=r"C:\work\same.sldprt")
        self._setup([doc1, doc2])
        result = server.sw_list_documents()
        assert result.count("[Part]") == 1

    def test_no_path_shows_fallback(self):
        doc = _make_doc("nopath.sldprt", path="")
        self._setup([doc])
        result = server.sw_list_documents()
        assert "(без шляху)" in result


# ──────────────────────────────────────────────────────────────
# sw_activate_document
# ──────────────────────────────────────────────────────────────

class TestSwActivateDocument:
    def _setup(self, docs):
        _docs = docs

        class FakeApp:
            def GetDocuments(self_):
                return _docs

            def ActivateDoc3(self_, path_or_title, silent, opts, err_ref=None):
                return 0

        server._sw = lambda: FakeApp()

    def test_match_by_path(self):
        doc = _make_doc("part.sldprt", path=r"C:\work\part.sldprt")
        self._setup([doc])
        result = server.sw_activate_document(r"C:\work\part.sldprt")
        assert "Активовано" in result

    def test_match_by_title(self):
        doc = _make_doc("part.sldprt")
        self._setup([doc])
        result = server.sw_activate_document("part.sldprt")
        assert "Активовано" in result

    def test_not_found(self):
        doc = _make_doc("other.sldprt")
        self._setup([doc])
        result = server.sw_activate_document("nonexistent.sldprt")
        assert "не знайдено" in result


# ──────────────────────────────────────────────────────────────
# sw_close_document
# ──────────────────────────────────────────────────────────────

class TestSwCloseDocument:
    def _setup(self, docs):
        _docs = docs
        closed = []

        class FakeApp:
            def GetDocuments(self_):
                return _docs

            def CloseDoc(self_, name):
                closed.append(name)

        server._sw = lambda: FakeApp()
        return closed

    def test_close_by_path(self):
        doc = _make_doc("part.sldprt", path=r"C:\work\part.sldprt")
        closed = self._setup([doc])
        result = server.sw_close_document(r"C:\work\part.sldprt")
        assert "Закрито" in result
        assert len(closed) == 1

    def test_close_by_title(self):
        doc = _make_doc("part.sldprt")
        closed = self._setup([doc])
        result = server.sw_close_document("part.sldprt")
        assert "Закрито" in result

    def test_save_before_close(self, mocker):
        doc = _make_doc("part.sldprt", path=r"C:\work\part.sldprt")
        doc.Save3 = mocker.MagicMock(return_value=None)
        self._setup([doc])
        server.sw_close_document(r"C:\work\part.sldprt", save=True)
        doc.Save3.assert_called_once_with(1, 0, 0)

    def test_no_save_when_flag_false(self, mocker):
        doc = _make_doc("part.sldprt", path=r"C:\work\part.sldprt")
        doc.Save3 = mocker.MagicMock()
        self._setup([doc])
        server.sw_close_document(r"C:\work\part.sldprt", save=False)
        doc.Save3.assert_not_called()

    def test_not_found(self):
        doc = _make_doc("other.sldprt")
        self._setup([doc])
        result = server.sw_close_document("ghost.sldprt")
        assert "не знайдено" in result
