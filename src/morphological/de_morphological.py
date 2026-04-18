import os

import spacy

spacy.prefer_gpu()
nlp = spacy.load("de_dep_news_trf", disable=["parser", "lemmatizer"])


def _parse_pipe_batch_size():
    value = os.environ.get("LTC_SPACY_PIPE_BATCH_SIZE")
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"LTC_SPACY_PIPE_BATCH_SIZE must be an integer: {value!r}"
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"LTC_SPACY_PIPE_BATCH_SIZE must be positive: {value!r}"
        )
    return parsed


_PIPE_BATCH_SIZE = _parse_pipe_batch_size()
_PIPE_KWARGS = (
    {"batch_size": _PIPE_BATCH_SIZE} if _PIPE_BATCH_SIZE is not None else {}
)
_BUCKETING = os.environ.get("LTC_BUCKETING", "0").lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _doc_to_tokens_and_tags(doc):
    mrph = []
    mrph_append = mrph.append
    tokenized = []
    tokenized_append = tokenized.append
    for token in doc:
        tokenized_append(token.text)
        tag = token.pos_
        # token = token.split("\t")
        # tokenized_append(token[0])
        # tag = token[1]
        if tag in ["ADJ"]:
            mrph_append("a")
        elif tag in ["NOUN", "PRON", "PROPN"]:
            mrph_append("n")
        elif tag in ["ADV", "CCONJ", "SCONJ"]:
            mrph_append("r")
        elif tag in ["VERB"]:
            mrph_append("v")
        else:
            mrph_append("")
    return tokenized, mrph


def de_morphological(sentence):
    return _doc_to_tokens_and_tags(nlp(sentence))


def _pipe_sorted_by_length(sentences):
    # char 長は token 数の近似。sort 安定で、sort cost は n log n で無視レベル
    order = sorted(range(len(sentences)), key=lambda i: len(sentences[i]), reverse=True)
    sorted_sents = [sentences[i] for i in order]
    tokenized = [None] * len(sentences)
    mrph = [None] * len(sentences)
    for pos, doc in enumerate(nlp.pipe(sorted_sents, **_PIPE_KWARGS)):
        tokenized_sentence, mrph_sentence = _doc_to_tokens_and_tags(doc)
        original_idx = order[pos]
        tokenized[original_idx] = tokenized_sentence
        mrph[original_idx] = mrph_sentence
    return tokenized, mrph


def de_morphological_batch(sentences):
    if _BUCKETING and len(sentences) > 1:
        return _pipe_sorted_by_length(sentences)
    tokenized = []
    mrph = []
    for doc in nlp.pipe(sentences, **_PIPE_KWARGS):
        tokenized_sentence, mrph_sentence = _doc_to_tokens_and_tags(doc)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph


# import spacy

# nlp = spacy.load("ko_core_news_sm")


# def ko_morphological(sentence):
#     doc = nlp(sentence)
#     mrph = []
#     mrph_append = mrph.append
#     tokenized = []
#     tokenized_append = tokenized.append
#     for token in doc:
#         tokenized_append(token.text)
#         tag = token.pos_
#         if tag in ["ADJ"]:
#             mrph_append("a")
#         elif tag in ["NOUN", "PRON", "PROPN"]:
#             mrph_append("n")
#         elif tag in ["ADV", "CCONJ", "SCONJ"]:
#             mrph_append("r")
#         elif tag in ["VERB"]:
#             mrph_append("v")
#         else:
#             mrph_append("")
#     return tokenized, mrph
