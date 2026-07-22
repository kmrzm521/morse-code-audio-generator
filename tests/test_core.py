from array import array

import pytest

from morse_app.core import (
    MorseToken,
    build_timeline,
    render_pcm,
    text_to_tokens,
)


def test_converts_letters_digits_and_punctuation():
    assert text_to_tokens("CQ 5?") == [
        MorseToken("C", "-.-."),
        MorseToken("Q", "--.-"),
        MorseToken(" ", "/"),
        MorseToken("5", "....."),
        MorseToken("?", "..--.."),
    ]


def test_short_digit_style_uses_cut_numbers():
    assert [token.code for token in text_to_tokens("0123456789", "short")] == [
        "-",
        ".-",
        "..-",
        "...-",
        "....-",
        ".....",
        "-....",
        "-...",
        "-..",
        "-.",
    ]


def test_prosign_is_one_morse_character():
    assert text_to_tokens("<AR>") == [MorseToken("AR", ".-.-.")]


def test_rejects_unknown_character():
    with pytest.raises(ValueError, match="不支持的字符"):
        text_to_tokens("你好")


def test_rejects_invalid_number_style():
    with pytest.raises(ValueError, match="数字编码"):
        text_to_tokens("123", "other")


def test_standard_timing_uses_one_three_seven_units():
    events = build_timeline(text_to_tokens("EE E"), character_wpm=20)
    tone_durations = [event.duration for event in events if event.kind == "tone"]
    silence_durations = [event.duration for event in events if event.kind == "silence"]
    assert tone_durations == pytest.approx([0.06, 0.06, 0.06])
    assert any(duration == pytest.approx(0.18) for duration in silence_durations)
    assert any(duration == pytest.approx(0.42) for duration in silence_durations)


def test_dash_and_internal_gap_have_three_to_one_ratio():
    events = build_timeline(text_to_tokens("A"), character_wpm=20)
    assert [event.kind for event in events] == ["tone", "silence", "tone"]
    assert [event.duration for event in events] == pytest.approx([0.06, 0.06, 0.18])


def test_farnsworth_preserves_tones_and_expands_spacing():
    tokens = text_to_tokens("PARIS PARIS")
    normal = build_timeline(tokens, character_wpm=20)
    slow = build_timeline(tokens, character_wpm=20, effective_wpm=10)
    assert [event.duration for event in normal if event.kind == "tone"] == pytest.approx(
        [event.duration for event in slow if event.kind == "tone"]
    )
    assert sum(event.duration for event in slow) > sum(event.duration for event in normal)


def test_farnsworth_requires_lower_effective_speed():
    with pytest.raises(ValueError, match="有效速度"):
        build_timeline(text_to_tokens("TEST"), 15, effective_wpm=15)


def test_pcm_has_expected_shape_and_faded_edges():
    pcm = render_pcm(build_timeline(text_to_tokens("E"), 20), 700)
    samples = array("h")
    samples.frombytes(pcm)
    assert len(samples) == round(44100 * 0.06)
    assert samples[0] == 0
    assert abs(samples[-1]) < 500
    assert max(abs(value) for value in samples) <= 32767


@pytest.mark.parametrize("frequency", [299, 1201])
def test_pcm_rejects_frequency_outside_supported_range(frequency):
    with pytest.raises(ValueError, match="300.*1200"):
        render_pcm(build_timeline(text_to_tokens("E"), 20), frequency)
