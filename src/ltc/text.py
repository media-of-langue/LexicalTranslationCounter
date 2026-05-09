"""Shared text normalization helpers."""


ENGLISH_PUNCT_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
    }
)


def normalize_english_text(text):
    return text.translate(ENGLISH_PUNCT_TRANSLATION)
