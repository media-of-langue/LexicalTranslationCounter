import os

import environ
import pandas as pd

env = environ.Env()
base = os.path.dirname(os.path.abspath(__file__))


"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""
pos_tag_rev = {"n": "noun", "a": "adj", "v": "verb", "r": "adverb"}

except_dict_dict = {}
for pos_tag in pos_tag_rev:
    path_normalize = os.path.normpath(
        os.path.join(base, "./normalize_data/zh/" + pos_tag + "_normalize.csv")
    )
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def zh_normalizer(word, pos_tag, wordlist, test=False):
    except_dict = except_dict_dict[pos_tag]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        word_normalized = word
    if word_normalized[-1] == "的":
        word_normalized = word_normalized[:-1]
    if test:
        return word_normalized
    tmp_key = "zh_" + pos_tag_rev[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        id = wordlist[tmp_key][word_normalized]
    else:
        id = None
    return id, word_normalized
