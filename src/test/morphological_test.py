import sys
import csv
import importlib
import os

# ensure src/ is on sys.path so the morphological package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

args = sys.argv
la1 = args[1]
la2 = args[2]
base = os.path.dirname(os.path.abspath(__file__))

la1_morphological = getattr(
    importlib.import_module(f"morphological.{la1}_morphological"),
    f"{la1}_morphological",
)
la2_morphological = getattr(
    importlib.import_module(f"morphological.{la2}_morphological"),
    f"{la2}_morphological",
)

# setting
langs = la1 + "_" + la2
input_path = os.path.normpath(os.path.join(base, "./data/corpus_" + langs + ".csv"))
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}
f_in = open(input_path, "r")
corpus_rows = csv.reader(f_in)

output_path = os.path.normpath(
    os.path.join(base, "./result_of_test/morphological_test_out_" + langs + ".txt")
)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
file = open(output_path, "w")

for corpus_row in corpus_rows:
    la1_words, la1_pos = la1_morphological(corpus_row[1])
    la2_words, la2_pos = la2_morphological(corpus_row[2])
    la1_result = ""
    la2_result = ""
    for i in range(len(la1_words)):
        if la1_pos[i] == "":
            la1_pos[i] = "N/A"
        la1_result += la1_words[i] + ":" + la1_pos[i] + " "
    for i in range(len(la2_words)):
        if la2_pos[i] == "":
            la2_pos[i] = "N/A"
        la2_result += la2_words[i] + ":" + la2_pos[i] + " "
    print(la1 + "_result", la1_result)
    print(la2 + "_result", la2_result)
    print("\n")

    file.write(la1_result + "\n")
    file.write(la2_result + "\n" + "\n")
f_in.close()
