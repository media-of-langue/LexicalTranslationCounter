import spacy

nlp = spacy.load("fr_dep_news_trf")


def fr_morphological(sentence):
    doc = nlp(sentence)
    mrph = []
    mrph_append = mrph.append
    tokenized = []
    tokenized_append = tokenized.append
    for token in doc:
        tokenized_append(token.text)
        tag = token.pos_
        if tag in ["ADJ"]:
            mrph_append("a")
        elif tag in ["NOUN", "PRON", "PROPN"]:
            mrph_append("n")
        elif tag in ["ADV", "CCONJ", "SCONJ"]:
            mrph_append("r")
        elif tag in ["VERB"]:
            mrph_append("v")
        else:
            mrph_append("")
    return tokenized, mrph
