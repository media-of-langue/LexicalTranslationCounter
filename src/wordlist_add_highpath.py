import csv
import sys
import re
import os

csv.field_size_limit(sys.maxsize)
la="ja"

highpath_dict = {
    "adj":10,
    "noun":30,
    "verb":10,
    "adverb":30,
}

wordlists_add_reader_dict = {
    "adj":csv.reader(open(f"./data/output/wordlist_{la}_added2_adj.csv", "r")),
    "noun":csv.reader(open(f"./data/output/wordlist_{la}_added2_noun.csv", "r")),
    "verb":csv.reader(open(f"./data/output/wordlist_{la}_added2_verb.csv", "r")),
    "adverb":csv.reader(open(f"./data/output/wordlist_{la}_added2_adverb.csv", "r")),
}
wordlists_add_writers_dict = {
    "adj":csv.writer(open(f"./data/output/wordlist_{la}_added_adj.csv", "w")),
    "noun":csv.writer(open(f"./data/output/wordlist_{la}_added_noun.csv", "w")),
    "verb":csv.writer(open(f"./data/output/wordlist_{la}_added_verb.csv", "w")),
    "adverb":csv.writer(open(f"./data/output/wordlist_{la}_added_adverb.csv", "w")),
}
part_of_speach_tag_code = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}

for pos_tag in wordlists_add_reader_dict:
    tmp_list = []
    for row in wordlists_add_reader_dict[pos_tag]:
        if int(row[1]) >= highpath_dict[pos_tag]:
            if pos_tag=="noun" and re.match(r"\d|%|\.|\(|\)|,", row[0]) is not None:
                continue
            elif pos_tag=="adj" and (row[0][-1]=="性" or row[0][-2:]=="たい"):
                continue
            tmp_list.append(row)
    wordlists_add_writers_dict[pos_tag].writerows(sorted(tmp_list, key=lambda x: x[1]))