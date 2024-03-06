from konlpy.tag import Komoran

komoran = Komoran()


def ko_morphological(sentence):
    try:
        doc = komoran.pos(sentence)
    except Exception as e:
        print(e)
        return [], []
    mrph = []
    mrph_append = mrph.append
    tokenized = []
    tokenized_append = tokenized.append
    for token in doc:
        tokenized_append(token[0])
        tag = token[1]
        if tag in ["VA", "XSA"]:
            mrph_append("a")
        elif tag in ["NNG", "NNP", "XSN", "NF"]:
            mrph_append("n")
        elif tag in ["MAG", "MAC", "MAJ"]:
            mrph_append("r")
        elif tag in ["VV", "VCP", "VCN", "XSV"]:
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
