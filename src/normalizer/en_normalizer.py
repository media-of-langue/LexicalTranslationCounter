"""
The normalizer exists for each language.
input: word(s),wordlist_la,pos
output: result{index:word_index, word:word_normalized}
"""

import os

import environ
import nltk
import pandas as pd

if not os.path.isdir("/root/nltk_data/tokenizers/punkt/"):
    nltk.download("punkt")
if not os.path.isfile("/root/nltk_data/corpora/wordnet.zip"):
    nltk.download("wordnet")
from nltk.stem.wordnet import WordNetLemmatizer

env = environ.Env()
lem = WordNetLemmatizer()
word_tokenizer = nltk.word_tokenize
base = os.path.dirname(os.path.abspath(__file__))
pos_list = ["adj", "adverb", "noun", "verb"]
except_dict_dict = {}

for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/en/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def en_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        tokenized_l = word_tokenizer(word)
        word_normalized = ""
        for token in tokenized_l:
            word_normalized += lem.lemmatize(token, pos) + " "
        if word_normalized != "":
            word_normalized = word_normalized[:-1]
    if test:
        return word_normalized
    tmp_key = "en_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        id_word = None
    return id_word, word_normalized
