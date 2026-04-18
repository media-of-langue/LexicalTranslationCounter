import sys
import csv
import importlib
import os

# ensure src/ is on sys.path so the normalizer package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

args = sys.argv
la = args[1]
input_word = args[2]
pos_tag_code = args[3]
# st_id=int(args[3])
# en_id=int(args[4])

normalizer = getattr(
    importlib.import_module(f"normalizer.{la}_normalizer"),
    f"{la}_normalizer",
)

# setting

part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

print(normalizer(input_word, pos_tag_code, "", test=True))