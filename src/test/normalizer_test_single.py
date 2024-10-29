import sys
import csv
import os
args = sys.argv
la = args[1]
input_word = args[2]
pos_tag_code = args[3]
# st_id=int(args[3])
# en_id=int(args[4])
base = os.path.dirname(os.path.abspath(__file__))
path_normalizer = os.path.normpath(os.path.join(base, '../normalizer/'))
sys.path.append(path_normalizer)
command = "from {}_normalizer import {}_normalizer as normalizer".format(la, la)
exec(command)

# setting

part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

print(normalizer(input_word, pos_tag_code, "", test=True))