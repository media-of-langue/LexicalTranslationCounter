## wordlistにデータをたす

import csv

la = "ja"

wordlist_dict = {
    "adj":csv.reader(open(f"./data/input/wordlist_{la}_adj.csv", "r")),
    "noun":csv.reader(open(f"./data/input/wordlist_{la}_noun.csv", "r")),
    "verb":csv.reader(open(f"./data/input/wordlist_{la}_verb.csv", "r")),
    "adverb":csv.reader(open(f"./data/input/wordlist_{la}_adverb.csv", "r")),
}

wordlist_add_dict = {
    "adj":csv.reader(open(f"./data/output/wordlist_{la}_added_adj.csv", "r")),
    "noun":csv.reader(open(f"./data/output/wordlist_{la}_added_noun.csv", "r")),
    "verb":csv.reader(open(f"./data/output/wordlist_{la}_added_verb.csv", "r")),
    "adverb":csv.reader(open(f"./data/output/wordlist_{la}_added_adverb.csv", "r")),
}

wordlist_new_writer_dict = {
    "adj":csv.writer(open(f"./data/output/wordlist_{la}_adj.csv", "w")),
    "noun":csv.writer(open(f"./data/output/wordlist_{la}_noun.csv", "w")),
    "verb":csv.writer(open(f"./data/output/wordlist_{la}_verb.csv", "w")),
    "adverb":csv.writer(open(f"./data/output/wordlist_{la}_adverb.csv", "w")),
}

for pos_tag in wordlist_dict:
    words = []
    id_max = 0
    for row in wordlist_dict[pos_tag]:
        words.append(row[1])
        id_max = max(id_max,int(row[0]))
        wordlist_new_writer_dict[pos_tag].writerow(row)
    for row in wordlist_add_dict[pos_tag]:
        if row[0] not in words:
            id_max += 1
            words.append(row[0])
            wordlist_new_writer_dict[pos_tag].writerow([id_max,row[0]])


