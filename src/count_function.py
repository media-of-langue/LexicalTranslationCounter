import csv
import sys
from multiprocessing import Process, Manager
import os
import pandas as pd
import traceback
import re
csv.field_size_limit(sys.maxsize)
args = sys.argv
start_id = int(args[1])
la1 = args[2]
la2 = args[3]
langs = la1 + "_" + la2
sys.path.append("/root/src/alignment/" + langs)
from alignment import alignment
base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, "../normalizer/"))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer_la1".format(la1, la1)
exec(command)
command = "from {}_normalizer import {}_normalizer as normalizer_la2".format(la2, la2)
exec(command)

# corpusを一行毎に読み出す
class CsvRowReader:
    def __init__(self, path):
        f = open(path, "r")
        self.file = f
        self.reader = csv.reader(f)
        self.offset_list = []
        while True:
            self.offset_list.append(f.tell())
            line = f.readline()
            if line == "":
                break
        self.offset_list.pop()  # remove offset at end of file
        self.num_rows = len(self.offset_list)

    def __del__(self):
        self.file.close()

    def read_row(self, idx):
        self.file.seek(self.offset_list[idx])
        return next(self.reader)


input_reader = CsvRowReader(f"./data/input/corpus_{langs}.csv")

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
    relations[pos_tag] = {}
    relations_id[pos_tag] = 0
    with open("./data/input/wordlist_" + la1 + "_" + pos_tag + ".csv", mode="r") as inp:
        reader = list(csv.reader(inp))
        if not re.fullmatch('[-+]?\d+',reader[0][0]):
            reader=reader[1:]
        wordlists[la1 + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
        max_id_la1 = max(wordlists[la1 + "_" + pos_tag].values())
    with open("./data/input/wordlist_" + la2 + "_" + pos_tag + ".csv", mode="r") as inp:
        reader = list(csv.reader(inp))
        if not re.fullmatch('[-+]?\d+',reader[0][0]):
            reader=reader[1:]
        wordlists[la2 + "_" + pos_tag] = {rows[1]: int(rows[0]) for rows in reader}
        max_id_la2 = max(wordlists[la2 + "_" + pos_tag].values())
    flag_la1 = False
    flag_la2 = False
    wordlists_add = {}
    wordlists_add[la1 + "_" + pos_tag] = {}
    wordlists_add[la2 + "_" + pos_tag] = {}
    for key,word_id in wordlists[la1 + "_" + pos_tag].items():
        if normalizer_la1(key,part_of_speach_tag_code[pos_tag],"",test=True) not in wordlists[la1 + "_" + pos_tag].keys():
            flag_la1 = True
            max_id_la1=max_id_la1 + 1
            wordlists_add[la1 + "_" + pos_tag][normalizer_la1(key,part_of_speach_tag_code[pos_tag],"",test=True)] = max_id_la1
    for key,word_id in wordlists[la2 + "_" + pos_tag].items():
        if normalizer_la2(key,part_of_speach_tag_code[pos_tag],"",test=True) not in wordlists[la2 + "_" + pos_tag].keys():
            flag_la2 = True
            max_id_la2=max_id_la2 + 1
            wordlists_add[la2 + "_" + pos_tag][normalizer_la2(key,part_of_speach_tag_code[pos_tag],"",test=True)] = max_id_la2
    print("wordlist_add",wordlists_add)
    wordlists[la1 + "_" + pos_tag].update(wordlists_add[la1 + "_" + pos_tag])
    wordlists[la2 + "_" + pos_tag].update(wordlists_add[la2 + "_" + pos_tag])
    if flag_la1:
        writer = csv.writer(open("./data/output/wordlist_" + la1 + "_" + pos_tag + ".csv", "w"))
        for key,word_id in wordlists[la1 + "_" + pos_tag].items():
            writer.writerow([word_id,key,"f"])
    if flag_la2:
        writer = csv.writer(open("./data/output/wordlist_" + la2 + "_" + pos_tag + ".csv", "w"))
        for key,word_id in wordlists[la2 + "_" + pos_tag].items():
            writer.writerow([word_id,key,"f"])

if start_id != 0:
    output_file = open(f"./data/output/corpus_{langs}.csv", "a")
    for pos_tag in part_of_speach_tag_rev.values():
        relations[pos_tag] = {}
        max_id = 0
        with open(
            "./data/output/relations_" + langs + "_" + pos_tag + "_totyu.csv", mode="r"
        ) as inp:
            reader = csv.reader(inp)
            for rows in reader:
                relations[pos_tag][rows[1] + "_" + rows[2]] = [
                    int(rows[0]),
                    int(rows[3]),
                    eval(rows[4]),
                    rows[5],
                    rows[6],
                ]
                if max_id > int(rows[0]):
                    max_id = int(rows[0])
            relations_id[pos_tag] = max_id + 1
    output_corpus_row_num = len([None for l in open(f"./data/output/corpus_{langs}.csv", "r")])
else:
    output_file = open(f"./data/output/corpus_{langs}.csv", "w")
    
if start_id == 0:
    passed_log_file = open("./data/output/passed_log.txt", "w")
else:
    passed_log_file = open("./data/output/passed_log.txt", "a")
output_writer = csv.writer(output_file)


def count_function(i, corpus_row, relations, relations_id, wordlists,output_corpus_row_num):
    if len(corpus_row) == 5:
        try:
            output_l = alignment(corpus_row, wordlists)
        except Exception as e:
            print(traceback.format_exc())
            passed_log_file.write(str(i))
            passed_log_file.write(str(corpus_row))
            output_l = []
        for index, command in enumerate(output_l):
            pos_tag = part_of_speach_tag_rev[command[0]]
            if command[1] + "_" + command[3] in relations[pos_tag]:
                relations[pos_tag][command[1] + "_" + command[3]][1] += 1
                relations[pos_tag][command[1] + "_" + command[3]][2].append(corpus_row[0])
                tmp_id = relations[pos_tag][command[1] + "_" + command[3]][0]
            else:
                tmp_id = relations_id[pos_tag]
                relations[pos_tag][command[1] + "_" + command[3]] = [
                    tmp_id,
                    1,
                    [corpus_row[0]],
                    "unknown",
                    False,
                ]
                relations_id[pos_tag] += 1
            output_l[index].insert(1, str(tmp_id))
        # command_t = "/".join([":".join(output) for output in output_l])
        if output_corpus_row_num <= i:
            output_writer.writerow(
                [corpus_row[0], corpus_row[1], corpus_row[2], "{"+str(output_l)[1:-1].replace('"',"")+"}", False]
            )
        print("passed_id:", i)
        print(corpus_row[1], corpus_row[2])
        print(output_l)
        print("\n")

try:
    for i in range(start_id, input_reader.num_rows):
        count_function(i,input_reader.read_row(i),relations,relations_id,wordlists,output_corpus_row_num)
        if i % 100000 == 0:
            for pos_tag in part_of_speach_tag_rev.values():
                with open(f'./data/output/relations_{langs}_{pos_tag}_totyu.csv', 'w') as f:
                    writer = csv.writer(f)
                    for key, value in relations[pos_tag].items():
                        [id_la1,id_la2] = key.split("_")
                        writer.writerow([value[0], id_la1,id_la2, value[1], value[2], value[3], value[4]])
            with open(f'./data/output/passed_id.txt', 'w') as f:
                f.write(str(i))
except Exception as e:
    print(traceback.format_exc())
finally:
    for pos_tag, relation in relations.items():
        with open(f"./data/output/relations_{langs}_{pos_tag}.csv", "w") as f:
            writer = csv.writer(f)
            for key, value in relation.items():
                [id_la1, id_la2] = key.split("_")
                writer.writerow(
                    [value[0], id_la1, id_la2, value[1], "{"+str(value[2])[1:-1]+"}", value[3], value[4]]
                )
