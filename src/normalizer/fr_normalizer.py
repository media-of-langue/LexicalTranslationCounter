import os
from french_lefff_lemmatizer.french_lefff_lemmatizer import FrenchLefffLemmatizer
import environ
import pandas as pd

env = environ.Env()
base = os.path.dirname(os.path.abspath(__file__))

pos_list = ["adj", "adv", "noun", "verb"]
lemmatizer = FrenchLefffLemmatizer()
except_dict_dict = {}
for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/fr/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def fr_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        word_normalized = lemmatizer.lemmatize(word, pos)
    if test:
        return word_normalized
    tmp_key = "fr_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        id_word = None
    return id_word, word_normalized
