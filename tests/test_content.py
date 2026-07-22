import random

import pytest

from morse_app.content import generate_group, generate_until_duration


@pytest.mark.parametrize(
    "mode",
    ["letters", "numbers", "mixed", "punctuation", "prosigns", "q_codes"],
)
def test_seeded_content_is_repeatable(mode):
    assert generate_group(mode, 5, random.Random(7)) == generate_group(
        mode, 5, random.Random(7)
    )


def test_group_has_requested_size():
    assert len(generate_group("letters", 7, random.Random(1))) == 7


def test_rejects_unknown_mode():
    with pytest.raises(ValueError, match="内容类型"):
        generate_group("unknown", 5, random.Random(1))


def test_generate_until_duration_keeps_complete_groups():
    text = generate_until_duration(
        "letters",
        group_size=5,
        target_seconds=2,
        timing_options={"character_wpm": 20, "number_style": "long"},
        rng=random.Random(4),
    )
    assert all(len(group) == 5 for group in text.split())
