import jieba.posseg as pseg

# 言語コードの参考サイト
# https://www.lancaster.ac.uk/fass/projects/corpus/ZCTC/annotation.htm

pos_code_dict = {
    "a": [
        "a",
        "ag",
        "al",
    ],
    "n": ["n", "an", "ng", "nl", "vn"],
    "v": ["v", "vf", "vg", "vi", "vl", "vshi", "vyou", "vx"],
    "r": ["ad", "d", "dg", "dn", "dl", "vd"],
    "prefix": ["h"],
    "suffix": ["k"],
    "de": ["uj"],
}

code_dict = {}
for pos, pos_codes in pos_code_dict.items():
    for pos_code in pos_codes:
        code_dict[pos_code] = pos


def zh_morphological(sentence):
    cut = pseg.cut(sentence)
    tokenized = []
    mrph = []
    tokenized_append = tokenized.append
    mrph_append = mrph.append
    pass_pos = ""
    for w in cut:
        pos = code_dict.get(w.flag, "")
        if pos != "suffix" and pos != "de":
            if pass_pos == "prefix":
                tokenized[-1] += w.word
                mrph[-1] = pos
            else:
                tokenized_append(w.word)
                mrph_append(pos)
            pass_pos = mrph[-1]
        elif pos == "de":
            tokenized[-1] += w.word
            mrph[-1] = "a"
        else:
            tokenized[-1] += w.word
            pass_pos = mrph[-1]
    return tokenized, mrph


def zh_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = zh_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph
