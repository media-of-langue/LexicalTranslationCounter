"""Shared constants used by the modernized LTC core."""

POS_TAG_TO_NAME = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}
POS_NAME_TO_TAG = {name: tag for tag, name in POS_TAG_TO_NAME.items()}
CONTENT_POS_NAMES = tuple(POS_NAME_TO_TAG.keys())
