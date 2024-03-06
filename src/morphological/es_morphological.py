import spacy

nlp = spacy.load("es_core_news_md")


def es_morphological(sentence):
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


def es_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = es_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)
    return tokenized, mrph
