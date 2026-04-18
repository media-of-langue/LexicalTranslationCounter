import sys
import csv
import importlib
import os

# ensure src/ is on sys.path so the morphological package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

args = sys.argv
la = args[1]
sentence_la = "そういうこともあります。"

la_morphological = getattr(
    importlib.import_module(f"morphological.{la}_morphological"),
    f"{la}_morphological",
)


# setting

part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

la_words, la_pos = la_morphological(sentence_la)
la_result = ""
la2_result = ""
for i in range(len(la_words)):
    if la_pos[i] == "":
        la_pos[i] = "N/A"
    la_result += la_words[i] + ":" + la_pos[i] + " "

print(la + "_result", la_result)
print("\n")