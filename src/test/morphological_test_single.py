import sys
import csv
import os

args = sys.argv
la = args[1]
sentence_la = "そういうこともあります。"
base = os.path.dirname(os.path.abspath(__file__))
path_morphological = os.path.normpath(os.path.join(base, "../morphological/"))
sys.path.append(path_morphological)
command1 = "from {}_morphological import {}_morphological as la_morphological".format(
    la, la
)
exec(command1)


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