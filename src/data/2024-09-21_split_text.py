import re
import os
import sys
import pandas as pd

chunk_size=1024
os.chdir(os.path.dirname(__file__))
text_path="en-it.txt"
save_folder="en_it_corpus"
save_file="en_it_corpus"
encode_type="utf-8"
os.makedirs(save_folder,exist_ok=True)
corpus_txt=open(text_path,"r")
line_num=0
text_list=[]

for line in corpus_txt: