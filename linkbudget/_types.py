"""
_types.py

Shared type aliases for the linkbudget package.
"""

from __future__ import annotations

from typing import Any, Dict, List

#: The result dict every component's ``propagate_signal`` returns and every
#: publisher consumes. Values are heterogeneous (floats, strings, ``None``,
#: bools), so the value type is ``Any``.
StageData = Dict[str, Any]

#: A computed budget -- the list of stage dicts on ``LinkContainer.data_list``.
StageList = List[Dict[str, Any]]
