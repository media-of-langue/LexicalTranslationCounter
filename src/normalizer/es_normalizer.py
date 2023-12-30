import os
import spacy
import pandas as pd
import environ

# spaCyのスペイン語中規模モデルをロード
nlp = spacy.load("es_core_news_md")

env = environ.Env()
base = os.path.dirname(os.path.abspath(__file__))

# spaCyのトークン化とレンマ化を使用
def spacy_tokenizer_lemmatizer(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

"""
normalizerは言語ごとに存在する
input:word(s),wordlist_la,pos
output:result{index:word_index, word:word_normalized}
"""
pos_tag_rev = {"n": "noun", "a": "adj", "v": "verb", "r": "adverb"}

except_dict_dict = {}
for pos_tag in pos_tag_rev:
    path_normalize = os.path.normpath(
        os.path.join(base, "./normalize_data/es/" + pos_tag + "_normalize.csv")
    )
    except_dict_dict[pos_tag] = pd.read_csv(
        path_normalize,
        header=None,
        index_col=0,
    ).to_dict()

def es_normalizer(word, pos_tag, wordlist, test=False):
    except_dict = except_dict_dict[pos_tag]
    if word in except_dict:
        word_normalized = except_dict[word]
    else:
        lemmatized_l = spacy_tokenizer_lemmatizer(word)
        word_normalized = " ".join(lemmatized_l)
    if test:
        return word_normalized
    tmp_key = "es_" + pos_tag_rev[pos_tag]
    if word_normalized in wordlist[tmp_key]:
        id = wordlist[tmp_key][word_normalized]
    else:
        id = None
    return id, word_normalized
