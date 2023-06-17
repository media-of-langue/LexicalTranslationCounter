import sys
import csv
import os

args = sys.argv
la = args[1]
base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, "../normalizer/"))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer".format(la, la)
exec(command)

part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

for pos_tag_code, pos_tag in part_of_speach_tag_rev.items():
    input_path = os.path.normpath(
        os.path.join(base, f"./data/wordlist_{la}_{pos_tag}.csv")
    )
    f_in = open(input_path)
    wordlist = csv.reader(f_in)
    output_path = os.path.normpath(
        os.path.join(
            base, "./result_of_test/normalizer_test_out_" + la + "_" + pos_tag + ".txt"
        )
    )
    file = open(output_path, "w")
    for word in wordlist:
        word_normalized = normalizer(word[1], pos_tag_code, "", test=True)
        if word[1] != word_normalized:
            print(word[1], "->", word_normalized)
            file.write(word[1] + "->" + word_normalized + "\n")
    f_in.close()
