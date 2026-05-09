import os

import nltk

from ltc.text import normalize_english_text


def ensure_nltk_resource(resource_paths, download_name):
    for resource_path in resource_paths:
        try:
            nltk.data.find(resource_path)
            return
        except LookupError:
            continue
    nltk.download(download_name)


ensure_nltk_resource(("corpora/omw-1.4", "corpora/omw-1.4.zip"), "omw-1.4")
ensure_nltk_resource(
    ("taggers/averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger.zip"),
    "averaged_perceptron_tagger",
)
ensure_nltk_resource(("tokenizers/punkt", "tokenizers/punkt.zip"), "punkt")
ensure_nltk_resource(("corpora/wordnet", "corpora/wordnet.zip"), "wordnet")
ensure_nltk_resource(("tokenizers/punkt_tab", "tokenizers/punkt_tab.zip"), "punkt_tab")
ensure_nltk_resource(
    (
        "taggers/averaged_perceptron_tagger_eng",
        "taggers/averaged_perceptron_tagger_eng.zip",
    ),
    "averaged_perceptron_tagger_eng",
)


def en_morphological(sentence):
    sentence = normalize_english_text(sentence)
    tokenized = nltk.word_tokenize(sentence)
    pos = nltk.pos_tag(tokenized)
    mrph = []
    mrph_append = mrph.append
    for con in pos:
        tag = con[1]
        if tag in ["JJ", "JJR", "JJS"]:
            mrph_append("a")
        elif tag in ["NN", "NNS", "NNP", "NNPS"]:
            mrph_append("n")
        elif tag in ["RB", "RBR", "RBS", "WRB"]:
            mrph_append("r")
        elif tag in ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]:
            mrph_append("v")
        else:
            mrph_append("")
    return tokenized, mrph


def en_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = en_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph
