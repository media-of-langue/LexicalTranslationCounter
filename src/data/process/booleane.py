import os
import re
import pandas as pd
os.chdir(os.path.dirname(__file__))
text=open("text.txt","r").read()

text=re.split("\n",text)
dict={
    "Prural":{},
    "複数":{},
    "過去":{},
    
}
for t in text:
    for k in dict.keys():
        if re.search(k,t) and (not re.search("の",t)):
            word=re.split("\t",t)[0]
            dict[k][word]=0

prurallist=list(dict["Prural"].keys())+list(dict["複数"].keys())
pastlist=list(dict["過去"].keys())

prurallist=pd.DataFrame(prurallist)
prurallist.to_parquet("prural.parquet")
prurallist=pd.DataFrame(pastlist)
prurallist.to_parquet("past.parquet")