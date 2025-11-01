import os

import nltk

ROOT = os.environ.get("ROOT", "/root")

if not os.path.isfile(f"{ROOT}/nltk_data/corpora/omw-1.4.zip"):
    nltk.download("omw-1.4")
if not os.path.isdir(f"{ROOT}/nltk_data/taggers/averaged_perceptron_tagger"):
    nltk.download("averaged_perceptron_tagger")
if not os.path.isdir(f"{ROOT}/nltk_data/tokenizers/punkt/"):
    nltk.download("punkt")
if not os.path.isfile(f"{ROOT}/nltk_data/corpora/wordnet.zip"):
    nltk.download("wordnet")

nltk.download("punkt_tab")
nltk.download("averaged_perceptron_tagger_eng")


def en_morphological(sentence):
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
