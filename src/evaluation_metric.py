"""The organisers' macro F1 (data/official/evaluation_script/main.py `_macro_f1`), imported unchanged."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "official_main", Path(__file__).resolve().parent.parent / "data/official/evaluation_script/main.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
macro_f1 = _mod._macro_f1
