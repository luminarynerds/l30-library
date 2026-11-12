import libcst as cst
from scripts.destyle.chain_raises import chain_raises


def _apply(src: str) -> str:
    return chain_raises(cst.parse_module(src)).code


def test_adds_from_e_when_named():
    src = '''try:
    pass
except ValueError as e:
    raise RuntimeError("oops")
'''
    out = _apply(src)
    assert "raise RuntimeError(\"oops\") from e" in out


def test_adds_from_none_when_unnamed():
    src = '''try:
    pass
except ValueError:
    raise RuntimeError("oops")
'''
    out = _apply(src)
    assert "raise RuntimeError(\"oops\") from None" in out


def test_adds_from_none_for_bare_except():
    src = '''try:
    pass
except:
    raise RuntimeError("oops")
'''
    out = _apply(src)
    assert "raise RuntimeError(\"oops\") from None" in out


def test_leaves_existing_chain_alone():
    src = '''try:
    pass
except ValueError as e:
    raise RuntimeError("oops") from e
'''
    out = _apply(src)
    assert out == src


def test_leaves_bare_raise_alone():
    src = '''try:
    pass
except ValueError:
    raise
'''
    out = _apply(src)
    assert out == src


def test_leaves_raise_outside_except_alone():
    src = '''def f():
    raise ValueError("oops")
'''
    out = _apply(src)
    assert out == src


def test_uses_innermost_except_name():
    src = '''try:
    pass
except ValueError as outer:
    try:
        pass
    except KeyError as inner:
        raise RuntimeError("oops")
'''
    out = _apply(src)
    assert "from inner" in out
    assert "from outer" not in out
