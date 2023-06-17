import sys
import csv
import os

args = sys.argv
la1 = args[1]
la2 = args[2]
base = os.path.dirname(os.path.abspath(__file__))
path_alignment = os.path.normpath(os.path.join(base, "../alignment/" + la1 + "_" + la2))
sys.path.append(path_alignment)

from alignment import alignment

# setting
langs = la1 + "_" + la2
corpus_name = "corpus_" + langs

cols = ["id", "word", "invalid"]
langs_l = [la1, la2]
input_path = os.path.normpath(os.path.join(base, "./data/corpus_" + langs + ".csv"))
f_in = open(input_path, "r")
corpus_rows = csv.reader(f_in)
part_of_speach_tag_rev = {"n": "noun", "v": "verb", "a": "adj", "r": "adverb"}

""" if test:
    relations_adj = [[0,0,10,"0:1:2"],[0,1,30,"3:4"]]
    relations_noun = [[0,0,15,"0:1"],[0,1,35,"3:4"]]
    word_ja_adj = [[0,"美しい"],[1,"綺麗"],[2,"かわいい"]]
    word_en_adj = [[0,"beautiful"],[1,"clean"],[2,"cute"]]
    word_ja_noun = [[0,"あなた"],[1,"人"]]
    word_en_noun = [[0,"you"],[1,"people"]]
    corpus = [["he is musician.","彼は音楽家だ","n:0:you:あなた/a:0:beautiful:綺麗だ "]] """
output_path = os.path.normpath(
    os.path.join(base, "./result_of_test/alignment_test_out_" + langs + ".txt")
)
file = open("./result_of_test/alignment_test_out_" + langs + ".txt", "w")
for corpus_row in corpus_rows:
    result = alignment(corpus_row, "", test=True)
    print("sentece_la1", corpus_row[1])
    print("sentece_la2", corpus_row[2])
    print("\nnew align")
    for align in result:
        print(align[2] + "-" + align[4])
    print("\n")

    file.write("sentece_la1:" + corpus_row[1] + "\n")
    file.write("sentece_la2:" + corpus_row[2] + "\n")
    file.write("new align\n")
    for align in result:
        file.write(align[2] + " - " + align[4] + "  ")
    file.write("\n" "\n")
f_in.close()
