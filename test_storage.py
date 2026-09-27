"""Run: python test_storage.py. Never touches production room data."""
import ast
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

source = ast.parse(Path(__file__).with_name("app.py").read_text())
helpers = ast.Module(body=[node for node in source.body
                          if isinstance(node, ast.FunctionDef)
                          and node.name in {"load_json", "save_json"}], type_ignores=[])
namespace = dict(Any=Any, json=json, os=os, tempfile=tempfile, Path=Path)
exec(compile(helpers, "app.py", "exec"), namespace)
load, save = namespace["load_json"], namespace["save_json"]
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "rooms.json"
    assert load(str(path)) == {}
    save(str(path), {"room": ["hello"]})
    assert load(str(path)) == {"room": ["hello"]}
    original = path.read_bytes()
    with patch.object(os, "replace", side_effect=OSError("disk failure")):
        try:
            save(str(path), {"room": []})
        except OSError:
            pass
        else:
            raise AssertionError("Write failure swallowed")
    assert path.read_bytes() == original
    assert list(Path(directory).iterdir()) == [path]
    for invalid in ["{broken", "[]", "null"]:
        path.write_text(invalid)
        try:
            load(str(path))
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid storage silently discarded")
        assert path.read_text() == invalid
print("Storage checks passed")
