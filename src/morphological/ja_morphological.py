from pyknp import Juman

jumanpp = Juman(timeout=300)

ja_nounsetsubi = [
    "症",
    "酢",
    "度",
    "感",
    "性",
    "法",
    "語",
    "系",
    "率",
    "律",
    "史",
    "論",
    "学",
    "観",
    "器",
    "集",
    "説",
    "録",
    "書",
    "等",
    "者",
    "制",
    "座",
]
indipendent_mrph = ["形容詞", "名詞", "動詞", "副詞"]


def ja_morphological(sentence):
    sentence = sentence.replace(" ", "")
    mrph_l = jumanpp.analysis(sentence).mrph_list()
    tokenized = []
    mrph_out = []
    tokenized_append = tokenized.append
    mrph_out_append = mrph_out.append
    last_katuyou2 = ""
    for mrph in mrph_l:
        if len(mrph_out) == 0 or len(tokenized) == 0:
            tokenized_append(mrph.midasi)
            mrph_out_append(mrph.hinsi)
            last_katuyou2 = mrph.katuyou2
        elif mrph.midasi in ja_nounsetsubi and (
            mrph_out[-1] == "名詞" or last_katuyou2 == "語幹"
        ):
            tokenized[-1] += mrph.midasi
            last_katuyou2 = ""
        elif mrph.hinsi == "接尾辞" and tokenized != [] and mrph.bunrui != "動詞性接尾辞":
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = mrph.bunrui[:-6]
            last_katuyou2 = ""
        elif (
            mrph.genkei == "する"
            and mrph.hinsi == "動詞"
            and mrph.katuyou1 == "サ変動詞"
            and mrph_out[-1] in indipendent_mrph
        ):
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = "動詞"
            last_katuyou2 = mrph.katuyou2
        elif mrph.hinsi == "名詞" and mrph_out[-1] == "接頭辞":
            tokenized[-1] += mrph.midasi
            mrph_out[-1] = "名詞"
            last_katuyou2 = mrph.katuyou2
        else:
            tokenized_append(mrph.midasi)
            mrph_out_append(mrph.hinsi)
            last_katuyou2 = mrph.katuyou2
    for i, con in enumerate(mrph_out):
        if con == "形容詞":
            mrph_out[i] = "a"
        elif con == "名詞":
            mrph_out[i] = "n"
        elif con == "動詞":
            mrph_out[i] = "v"
        elif con == "副詞":
            mrph_out[i] = "r"
        else:
            mrph_out[i] = ""
    return tokenized, mrph_out
