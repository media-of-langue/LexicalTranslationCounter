"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""

import os

import pandas as pd
from germalemma import GermaLemma

lemmatizer = GermaLemma()

base = os.path.dirname(os.path.abspath(__file__))

pos_list = ["adj", "adverb", "noun", "verb"]
pos_for_germalemma = {"adj": "ADJ", "adverb": "ADV", "noun": "N", "verb": "V"}
except_dict_dict = {}
for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/de/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def de_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        word_normalized = lemmatizer.find_lemma(word, pos_for_germalemma[pos])
    if test:
        return word_normalized
    tmp_key = "de_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        id_word = None
    return id_word, word_normalized
