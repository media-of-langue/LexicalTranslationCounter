import os

import nltk

if not os.path.isdir("/root/nltk_data/tokenizers/punkt/"):
    nltk.download("punkt")
if not os.path.isfile("/root/nltk_data/corpora/wordnet.zip"):
    nltk.download("wordnet")
import environ
import pandas as pd
from nltk.stem.wordnet import WordNetLemmatizer
from konlpy.tag import Komoran

komoran = Komoran()
base = os.path.dirname(os.path.abspath(__file__))
env = environ.Env()
lem = WordNetLemmatizer()
word_tokenizer = nltk.word_tokenize

"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""
pos_tag_rev = {"n": "noun", "a": "adj", "v": "verb", "r": "adverb"}

except_dict_dict = {}
for pos_tag in pos_tag_rev:
    path_normalize = os.path.normpath(
        os.path.join(base, "./normalize_data/ko/" + pos_tag + "_normalize.csv")
    )
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def ko_normalizer(word, pos_tag, wordlist, test=False):
    except_dict = except_dict_dict[pos_tag]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        komoran_morphs = komoran.pos(word)
        word_normalized = ""
        if pos_tag == "a":
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
        elif pos_tag == "v":
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
        elif pos_tag == "r":
            word_normalized += word
        elif pos_tag == "n":
            word_normalized += word
    if test:
        return word_normalized
    tmp_key = "ko_" + pos_tag_rev[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        id = wordlist[tmp_key][word_normalized]
    else:
        id = None
    return id, word_normalized
