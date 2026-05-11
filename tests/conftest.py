"""
Підміняємо win32com / pythoncom ще до імпорту server.py,
щоб тести запускались на будь-якій ОС (Linux, macOS, CI).
"""
import sys
import types
import pytest


def _make_win32_stub():
    win32com = types.ModuleType("win32com")
    win32com.client = types.ModuleType("win32com.client")
    win32com.client.Dispatch = lambda *a, **kw: None
    win32com.client.VARIANT = lambda *a, **kw: None
    sys.modules["win32com"] = win32com
    sys.modules["win32com.client"] = win32com.client

    pythoncom = types.ModuleType("pythoncom")
    pythoncom.CoInitialize = lambda: None
    pythoncom.VT_BYREF = 0
    pythoncom.VT_I4 = 0
    sys.modules["pythoncom"] = pythoncom

    fastmcp = types.ModuleType("fastmcp")

    class _FakeMCP:
        def __init__(self, *a, **kw):
            pass

        def tool(self):
            def decorator(fn):
                return fn
            return decorator

        def run(self):
            pass

    fastmcp.FastMCP = _FakeMCP
    sys.modules["fastmcp"] = fastmcp


_make_win32_stub()

import server  # noqa: E402  (must come after stubs)


@pytest.fixture(autouse=True)
def reset_swapp():
    """Скидає глобальний swApp між тестами."""
    original = server.swApp
    yield
    server.swApp = original
