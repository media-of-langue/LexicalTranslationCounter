import spacy

nlp = spacy.load("it_core_news_sm")


def it_morphological_batch(sentences):
    docs = list(nlp.pipe(sentences))
    tokenized = []
    mrph = []

    for doc in docs:
        tokenized_sentence = [token.text for token in doc]
        mrph_sentence = [get_morphological_tag(token.pos_) for token in doc]
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph


def it_morphological(sentence):
    doc = nlp(sentence)
    tokenized = [token.text for token in doc]
    mrph = [get_morphological_tag(token.pos_) for token in doc]
    return tokenized, mrph


def get_morphological_tag(tag):
    morph_tags = {
        "ADJ": "a",
        "NOUN": "n",
        "PRON": "n",
        "PROPN": "n",
        "ADV": "r",
        "CCONJ": "r",
        "SCONJ": "r",
        "VERB": "v",
    }
    return morph_tags.get(tag, "")
