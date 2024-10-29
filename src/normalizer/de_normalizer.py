import os
import pandas as pd
from germalemma import GermaLemma
import sys


lemmatizer = GermaLemma()

base = os.path.dirname(os.path.abspath(__file__))


"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""
pos_tag_rev = {"n": "noun", "a": "adj", "v": "verb", "r": "adverb"}
pos_tag_to_germalemma = {"n": "N", "a": "ADJ", "v": "V", "r": "ADV"}

except_dict_dict = {}
for pos_tag in pos_tag_rev:
    path_normalize = os.path.normpath(
        os.path.join(base, "./normalize_data/de/" + pos_tag + "_normalize.csv")
    )
    print(pos_tag)
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()
    # print(except_dict_dict[pos_tag])
    # for k, v in except_dict_dict[pos_tag].items():
    # print(k, "\n", v, "\n")
   
    except_dict_dict[pos_tag] = except_dict_dict[pos_tag][1]
    #print(except_dict_dict[pos_tag])

    # if "Kollegin" in except_dict_dict[pos_tag].keys():
    # print("good")


def de_normalizer(word, pos_tag, wordlist, test=False):


    except_dict = except_dict_dict[pos_tag]
    if word in except_dict:
        word_normalized = except_dict[word]
        #print(word,word_normalized)
        

    else:
        word_normalized = lemmatizer.find_lemma(word, pos_tag_to_germalemma[pos_tag])
    if test:
        return word_normalized
    tmp_key = "de_" + pos_tag_rev[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        id = wordlist[tmp_key][word_normalized]
    else:
        id = None
    return id, word_normalized
