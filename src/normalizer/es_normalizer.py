"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""

import os
import spacy
import pandas as pd
import environ

env = environ.Env()
base = os.path.dirname(os.path.abspath(__file__))
# spaCyのスペイン語中規模モデルをロード
nlp = spacy.load("es_core_news_md")


# spaCyのトークン化とレンマ化を使用
def spacy_tokenizer_lemmatizer(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]


pos_list = ["adj", "adverb", "noun", "verb"]
except_dict_dict = {}

for pos in pos_list:
    path_normalize = os.path.normpath(
        os.path.join(base, "./data/es/" + pos + "_normalize.csv")
    )
    except_dict_dict[pos] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()


def es_normalizer(word, pos, wordlist, test=False):
    except_dict = except_dict_dict[pos]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        lemmatized_l = spacy_tokenizer_lemmatizer(word)
        word_normalized = " ".join(lemmatized_l)
    if test:
        return word_normalized
    tmp_key = "es_" + pos_list[pos]
    if word_normalized in wordlist[tmp_key]:
        id_word = wordlist[tmp_key][word_normalized]
    else:
        id_word = None
    return id_word, word_normalized
