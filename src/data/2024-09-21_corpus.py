import re
import os
import sys
import pandas as pd

chunk_size=10**5
os.chdir(os.path.dirname(__file__))
text_path="en-it.txt"
save_folder="/Volumes/K_MAKOTO/MOL/LexicalTranslationCounter/src/data/en_it_corpus"
save_file="en_it_corpus"
encode_type="utf-8"
os.makedirs(save_folder,exist_ok=True)
corpus_txt=open(text_path,"r")
line_num=0
text_list=[]

for line in corpus_txt:
    la1_txt=""
    la2_txt=""
    example_txt_list=re.split("\t",line)
    la1=True
    for example_txt in example_txt_list:
        if not example_txt=="":
            if la1:
                la1_txt=example_txt
                la1=False
            else:
                la2_txt=example_txt
    text_list.append([line_num,la2_txt,la1_txt,{},False])
    
    line_num+=1
    if line_num%chunk_size==0:
        print(f"\r{str(int(line_num/chunk_size)).zfill(5)}",end="")
        text_list=pd.DataFrame(text_list)
        text_list.to_csv(f"{save_folder}/{save_file}_{str(int(line_num/chunk_size)).zfill(5)}.csv",index="",header="",encoding=encode_type)
        text_list=[]
text_list=pd.DataFrame(text_list)
text_list.to_csv(f"{save_folder}/{save_file}_{str(int(line_num/chunk_size)+1).zfill(5)}.csv",index="",header="",encoding=encode_type)

    
            