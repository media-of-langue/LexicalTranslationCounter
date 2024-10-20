import os

import nltk

if not os.path.isdir("/root/nltk_data/tokenizers/punkt/"):
    nltk.download("punkt")
if not os.path.isfile("/root/nltk_data/corpora/wordnet.zip"):
    nltk.download("wordnet")
import environ
import pandas as pd
from nltk.stem import SnowballStemmer
from nltk.stem.wordnet import WordNetLemmatizer

env = environ.Env()
base = os.path.dirname(os.path.abspath(__file__))

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
        os.path.join(base, "./normalize_data/it/" + pos_tag + "_normalize.csv")
    )
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()
    except_dict_dict[pos_tag] = except_dict_dict[pos_tag][1]


def it_normalizer(word, pos_tag, wordlist, test=False):
    except_dict = except_dict_dict[pos_tag]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        tokenized_l = word_tokenizer(word)
        word_normalized = ""
        for token in tokenized_l:
            word_normalized += lem.lemmatize(token, pos_tag) + " "
        if word_normalized != "":
            word_normalized = word_normalized[:-1]
    if test:
        return word_normalized
    tmp_key = "it_" + pos_tag_rev[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        id = wordlist[tmp_key][word_normalized]
    else:
        id = None
    return id, word_normalized
