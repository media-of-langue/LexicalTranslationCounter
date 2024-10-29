from pyknp import Juman

jumanpp = Juman(timeout=300,jumanpp=True)

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
    "員",
    "体",
    "生",
    "帯",
    "量",
    "分",
    "数",
    "作用",
    "機",
    "器",
    "盤",
    "金",
    "種",
    "地",
    "場",
    "先",
    "軍",
    "業",
    "物",
    "中",
    "者",
    "権",
    "室",
    "線",
    "教",
    "丸",
    "界"
]
indipendent_mrph = ["形容詞", "名詞", "動詞", "副詞"]


def ja_morphological(sentence):
    sentence = sentence.replace(" ", "")
    try:
        mrph_l = jumanpp.analysis(sentence).mrph_list()
    except Exception as e:
        print("jumanpp error", e)
        print("sentence", sentence)

    tokenized = []
    mrph_out = []
    tokenized_append = tokenized.append
    mrph_out_append = mrph_out.append
    last_katuyou2 = ""
    for mrph in mrph_l:
        
        if len(mrph_out) == 0 or len(tokenized) == 0:
            print(mrph.midasi)
            tokenized_append(mrph.midasi)
            mrph_out_append(mrph.hinsi)
            last_katuyou2 = mrph.katuyou2
        elif mrph.midasi in ja_nounsetsubi and tokenized != [] and (
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
        elif mrph.hinsi == "名詞" and tokenized != [] and mrph_out[-1] == "名詞":
            tokenized[-1] += mrph.midasi
            last_katuyou2 = mrph.katuyou2
        elif mrph.hinsi == "動詞" and tokenized != [] and mrph_out[-1] == "動詞":
            tokenized[-1] += mrph.midasi
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


def ja_morphological_batch(sentences):
    tokenized = []
    mrph = []
    for sentence in sentences:
        tokenized_sentence, mrph_sentence = ja_morphological(sentence)
        tokenized.append(tokenized_sentence)
        mrph.append(mrph_sentence)

    return tokenized, mrph

if __name__=="__main__":
    print(ja_morphological("明日は晴れの可能性が高いのだ"))