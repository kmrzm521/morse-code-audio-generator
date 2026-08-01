import ast
import re
from pathlib import Path

from morse_app.gui import MODE_LABELS, NUMBER_STYLE_LABELS, OUTPUT_FORMAT_LABELS


FORBIDDEN_VISIBLE_ENGLISH = re.compile(
    r"[a-z]|WPM|Hz|LRC|MP3|WAV|Farnsworth|Morse",
    re.IGNORECASE,
)


def _strings(value):
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        yield value.value
    elif isinstance(value, (ast.Tuple, ast.List)):
        for item in value.elts:
            yield from _strings(item)


def _visible_text(path: str):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    visible = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg in {"text", "title", "values"}:
                visible.extend(_strings(keyword.value))
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "title",
            "showerror",
            "showinfo",
        }:
            for argument in node.args[:2]:
                visible.extend(_strings(argument))

    return visible


def test_static_user_visible_gui_text_is_chinese():
    visible = _visible_text("morse_app/gui.py") + _visible_text(
        "morse_app/license_admin_gui.py"
    )
    offenders = [text for text in visible if FORBIDDEN_VISIBLE_ENGLISH.search(text)]
    assert offenders == []


def test_all_display_mapping_keys_are_chinese():
    labels = tuple(MODE_LABELS) + tuple(NUMBER_STYLE_LABELS) + tuple(OUTPUT_FORMAT_LABELS)
    assert not any(FORBIDDEN_VISIBLE_ENGLISH.search(label) for label in labels)
