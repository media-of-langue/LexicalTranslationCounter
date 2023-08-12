from konlpy.tag import Komoran

komoran = Komoran()


def ko_morphological(sentence):
    doc = komoran.pos(sentence)
    mrph = []
    mrph_append = mrph.append
    tokenized = []
    tokenized_append = tokenized.append
    for token in doc:
        tokenized_append(token[0])
        tag = token[1]
        if tag in ["VA"]:
            mrph_append("a")
        elif tag in ["NNG"]:
            mrph_append("n")
        elif tag in ["MAG", "MAC"]:
            mrph_append("r")
        elif tag in ["VV", "VCP", "VCN"]:
            mrph_append("v")
        else:
            mrph_append("")
    return tokenized, mrph


def ko_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = ko_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph


# import spacy

# nlp = spacy.load("ko_core_news_sm")


# def ko_morphological(sentence):
#     doc = nlp(sentence)
#     mrph = []
#     mrph_append = mrph.append
#     tokenized = []
#     tokenized_append = tokenized.append
#     for token in doc:
#         tokenized_append(token.text)
#         tag = token.pos_
#         if tag in ["ADJ"]:
#             mrph_append("a")
#         elif tag in ["NOUN", "PRON", "PROPN"]:
#             mrph_append("n")
#         elif tag in ["ADV", "CCONJ", "SCONJ"]:
#             mrph_append("r")
#         elif tag in ["VERB"]:
#             mrph_append("v")
#         else:
#             mrph_append("")
#     return tokenized, mrph
