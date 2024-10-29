import sys
import os

args = sys.argv
la1 = args[1]
la2 = args[2]
sentence_la1 = "For a surcharge, guests may use a shuttle from the airport to the hotel (available on request) and a ferry terminal shuttle."
sentence_la2 = "住客可付费乘坐(按要求提供)从机场到酒店的班车和渡轮码头接驳班车。 参阅更多 服务"
base = os.path.dirname(os.path.abspath(__file__))
path_alignment = os.path.normpath(os.path.join(base, "../alignment/" + la1 + "_" + la2))
sys.path.append(path_alignment)

from alignment import alignment

# setting
langs = la1 + "_" + la2

langs_l = [la1, la2]
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

result = alignment([0,sentence_la1,sentence_la2], "", test=True)
print("sentece_la1", sentence_la1)
print("sentece_la2", sentence_la2)
print("\nnew align")
for align in result:
    print(align[2] + "-" + align[4])
print("\n")