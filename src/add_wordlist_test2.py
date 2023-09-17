import csv 
import sys
import os

csv.field_size_limit(sys.maxsize)
la = "ja"
start_id = 0
langs = "en_ja"
base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, "./normalizer/"))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer_la".format(la,la)
exec(command)

wordlists_add_reader_dict = {
    "adj":csv.reader(open(f"./data/output/wordlist_{la}_added_adj.csv", "r")),
    "noun":csv.reader(open(f"./data/output/wordlist_{la}_added_noun.csv", "r")),
    "verb":csv.reader(open(f"./data/output/wordlist_{la}_added_verb.csv", "r")),
    "adverb":csv.reader(open(f"./data/output/wordlist_{la}_added_adverb.csv", "r")),
}
wordlists_add_writers_dict = {
    "adj":csv.writer(open(f"./data/output/wordlist_{la}_added2_adj.csv", "w")),
    "noun":csv.writer(open(f"./data/output/wordlist_{la}_added2_noun.csv", "w")),
    "verb":csv.writer(open(f"./data/output/wordlist_{la}_added2_verb.csv", "w")),
    "adverb":csv.writer(open(f"./data/output/wordlist_{la}_added2_adverb.csv", "w")),
}
part_of_speach_tag_code = {"noun": "n", "verb": "v", "adj": "a", "adverb": "r"}

for pos_tag in wordlists_add_reader_dict:
    for row in wordlists_add_reader_dict[pos_tag]:
        mrph = part_of_speach_tag_code[pos_tag]
        wordlists_add_writers_dict[pos_tag].writerow([normalizer_la(row[0],mrph,"",test=True),row[1]])
