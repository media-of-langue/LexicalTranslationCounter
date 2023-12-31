import csv
import sys
from multiprocessing import Process, Manager
import os
import pandas as pd
import re

csv.field_size_limit(sys.maxsize)
la = "es"
start_id = 0
la1 = "en"
la2 = "es"
langs = la1 + "_" + la2
base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, "./normalizer/"))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer_la".format(la,la)
exec(command)

path_morphological = os.path.normpath(os.path.join(base, "./morphological/"))
sys.path.append(path_morphological)
command = "from {}_morphological import {}_morphological as morphological_la1".format(la1,la1)
exec(command)
command = "from {}_morphological import {}_morphological as morphological_la2".format(la2,la2)
exec(command)

highpath_dict = {
    "adj":10,
    "noun":30,
    "verb":10,
    "adverb":30,
}

# corpusを一行毎に読み出す
class CsvRowReader:
    def __init__(self, path):
        f = open(path, "r", encoding="utf_8")
        self.file = f
        self.reader = csv.reader(f)
        self.offset_list = []
        while True:
            self.offset_list.append(f.tell())
            line = f.readline()
            if line == "":
                break
            # if len(self.offset_list) >= 201:
            #     break
        self.offset_list.pop()  # remove offset at end of file
        self.num_rows = len(self.offset_list)

    def __del__(self):
        self.file.close()

    def read_row(self, idx):
        self.file.seek(self.offset_list[idx])
        return next(self.reader)


input_reader = CsvRowReader(f"./data/input/corpus_{langs}_s.csv")

# check if output directory exists
if not os.path.isdir("./data/output"):
    os.makedirs("./data/output")

part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}
part_of_speach_tag_code = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}
relations = {}  # {pos_tag:{id_la1}_{id_la2}:[id,count,example,convert_from,invalid]}
relations_id = {}  # {pos_tag:id}
wordlists = {}  # {pos_tag:{word:id}}
process_list = []
output_corpus_row_num = 0
for pos_tag in part_of_speach_tag_rev.values():
    # with open("./data/input/wordlist_" + la + "_" + pos_tag + ".csv", mode="r") as inp:
    #     reader = list(csv.reader(inp))
    #     if not re.fullmatch("[-+]?\d+", reader[0][0]):
    #         reader = reader[1:]
    #     wordlists[la + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
        # max_id_la1 = max(wordlists[la + "_" + pos_tag].values())
    wordlists[la + "_" + pos_tag] = {}
    max_id_la1 = 0
    wordlists_add = {}
    wordlists_add[la + "_" + pos_tag] = {}
    for key, word_id in wordlists[la + "_" + pos_tag].items():
        if (
            normalizer_la(key, part_of_speach_tag_code[pos_tag], "", test=True)
            not in wordlists[la + "_" + pos_tag].keys()
        ):
            flag_la1 = True
            max_id_la1 = max_id_la1 + 1
            wordlists_add[la + "_" + pos_tag][
                normalizer_la(key, part_of_speach_tag_code[pos_tag], "", test=True)
            ] = max_id_la1
    print("wordlist_add", wordlists_add)
    wordlists[la + "_" + pos_tag].update(wordlists_add[la + "_" + pos_tag])
print(wordlists)
wordlists_add_cnt_dict = {
    "adj":{},
    "noun":{},
    "verb":{},
    "adverb":{},
}
cnt = 0
for i  in range(input_reader.num_rows):
    row = input_reader.read_row(i)
    if la == la1:
        sentence = row[1].replace("@", "")
        tokenized,morphs = morphological_la1(sentence)
    elif la == la2:
        sentence = row[2].replace("@", "")
        tokenized,morphs = morphological_la2(sentence)
    for token,morph in zip(tokenized,morphs):
        if morph != "":
            word_normalized = normalizer_la(token,morph,"",test=True)
            pos = part_of_speach_tag_rev[morph]
            if word_normalized not in wordlists[la + "_" + pos]:
                if word_normalized in wordlists_add_cnt_dict[pos]:
                    wordlists_add_cnt_dict[pos][word_normalized] += 1
                else:
                    wordlists_add_cnt_dict[pos][word_normalized] = 1
    cnt += 1
    if cnt % 10000 == 0:
        print("cnt", cnt)
wordlist_new_writer_dict = {
    "adj":csv.writer(open(f"./data/output/wordlist_{la}_adj.csv", "w")),
    "noun":csv.writer(open(f"./data/output/wordlist_{la}_noun.csv", "w")),
    "verb":csv.writer(open(f"./data/output/wordlist_{la}_verb.csv", "w")),
    "adverb":csv.writer(open(f"./data/output/wordlist_{la}_adverb.csv", "w")),
}
for pos_tag in wordlists_add_cnt_dict:
    words = []
    id_max = 0
    for key in wordlists[la+"_"+pos_tag]:
        words.append(key)
        wordlist_new_writer_dict[pos_tag].writerow([id_max,key])
        id_max += 1
    for wordnormlized in wordlists_add_cnt_dict[pos_tag]:
        if wordnormlized not in words and wordlists_add_cnt_dict[pos_tag][wordnormlized] >= highpath_dict[pos_tag]:
            words.append(wordnormlized)
            wordlist_new_writer_dict[pos_tag].writerow([id_max,wordnormlized])
            id_max += 1