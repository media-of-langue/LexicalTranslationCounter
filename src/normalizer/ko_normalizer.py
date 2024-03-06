"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""

import os

import environ
import pandas as pd
import nltk

if not os.path.isdir("/root/nltk_data/tokenizers/punkt/"):
    nltk.download("punkt")
if not os.path.isfile("/root/nltk_data/corpora/wordnet.zip"):
    nltk.download("wordnet")

from nltk.stem.wordnet import WordNetLemmatizer
from konlpy.tag import Komoran

env = environ.Env()
word_tokenizer = nltk.word_tokenize
lem = WordNetLemmatizer()
komoran = Komoran()
base = os.path.dirname(os.path.abspath(__file__))
pos_list = ["adj", "adverb", "noun", "verb"]
except_dict_dict = {}

for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/ko/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def ko_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        komoran_morphs = komoran.pos(word)
        word_normalized = ""
        if pos == "adj":
            for morph, tag in komoran_morphs:
                if tag.startswith("VV") or tag.startswith("VA") or tag.startswith("VX"):
                    word_normalized += morph
                elif tag.startswith("X"):
                    word_normalized += morph
                elif tag.startswith("NNG"):
                    word_normalized += morph
                elif tag.startswith("NNP"):
                    word_normalized += morph
            if word_normalized != "" and word_normalized[-1] != "다":
                word_normalized += "다"
        elif pos == "verb":
            for morph, tag in komoran_morphs:
                if tag.startswith("VV") or tag.startswith("VA") or tag.startswith("VX"):
                    word_normalized += morph
                elif tag.startswith("X"):
                    word_normalized += morph
                elif tag.startswith("NNG"):
                    word_normalized += morph
                elif tag.startswith("NNP"):
                    word_normalized += morph
                elif tag.startswith("MAG"):
                    word_normalized += morph
            if len(word_normalized) > 0 and word_normalized[-1] != "다":
                word_normalized += "다"
        elif pos == "adverb":
            word_normalized += word
        elif pos == "noun":
            word_normalized += word
    if test:
        return word_normalized
    tmp_key = "ko_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        id_word = None
    return id_word, word_normalized
