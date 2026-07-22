import pytest

from morse_app.core import MorseToken, text_to_tokens


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
