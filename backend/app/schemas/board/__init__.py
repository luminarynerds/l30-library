"""Board schemas -- split from monolithic board.py for maintainability.

All schemas are re-exported here so existing imports continue to work:
    from ....schemas.board import BoardMeetingCreate  # still works
"""
from ._all import *  # noqa: F401,F403
