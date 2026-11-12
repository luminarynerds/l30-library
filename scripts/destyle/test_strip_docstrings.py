import libcst as cst
from scripts.destyle.strip_docstrings import find_internal_docstrings

ROUTE_MODULE = '''
from fastapi import APIRouter

router = APIRouter()


@router.get("/items")
def list_items():
    """List all items.

    Public endpoint exposed via Swagger.
    """
    return []


def _normalize(s: str) -> str:
    """Lowercase and strip whitespace."""
    return s.lower().strip()


class _Helper:
    """Private helper class."""

    def run(self):
        """Do the thing."""
        return None
'''


def test_skips_router_decorated_functions():
    tree = cst.parse_module(ROUTE_MODULE)
    hits = find_internal_docstrings(tree, file_path="app/api/v1/items.py")
    names = {h.qualified_name for h in hits}
    assert "list_items" not in names


def test_finds_internal_function():
    tree = cst.parse_module(ROUTE_MODULE)
    hits = find_internal_docstrings(tree, file_path="app/api/v1/items.py")
    names = {h.qualified_name for h in hits}
    assert "_normalize" in names


def test_finds_internal_class_and_method():
    tree = cst.parse_module(ROUTE_MODULE)
    hits = find_internal_docstrings(tree, file_path="app/api/v1/items.py")
    names = {h.qualified_name for h in hits}
    assert "_Helper" in names
    assert "_Helper.run" in names


from scripts.destyle.strip_docstrings import strip_docstrings


def test_strip_removes_internal_docstring():
    tree = cst.parse_module(ROUTE_MODULE)
    stripped = strip_docstrings(tree, file_path="app/api/v1/items.py")
    code = stripped.code
    assert "Lowercase and strip whitespace." not in code
    assert "Private helper class." not in code
    assert "Do the thing." not in code


def test_strip_keeps_router_docstring():
    tree = cst.parse_module(ROUTE_MODULE)
    stripped = strip_docstrings(tree, file_path="app/api/v1/items.py")
    code = stripped.code
    assert "List all items." in code


from scripts.destyle.strip_module_headers import strip_module_header

MODULE_WITH_HEADER = '''"""Handles patron registration.

Used by the FastAPI router to validate sign-up.
"""
from pydantic import BaseModel


class Patron(BaseModel):
    name: str
'''


def test_strip_module_header_removes_top_docstring():
    tree = cst.parse_module(MODULE_WITH_HEADER)
    stripped = strip_module_header(tree, file_path="backend/app/patrons/models.py")
    assert "Handles patron registration." not in stripped.code
    assert "class Patron" in stripped.code


def test_strip_module_header_keeps_api_docs():
    tree = cst.parse_module(MODULE_WITH_HEADER)
    stripped = strip_module_header(tree, file_path="backend/app/api/v1/patrons.py")
    assert "Handles patron registration." in stripped.code


def test_strip_module_header_keeps_init():
    tree = cst.parse_module(MODULE_WITH_HEADER)
    stripped = strip_module_header(tree, file_path="backend/app/patrons/__init__.py")
    assert "Handles patron registration." in stripped.code
