import os 
import pandas as pd

os.chdir(os.path.dirname(__file__))
data=pd.read_csv("a_normalize.csv",encoding="shift-jis")
data.to_csv("a_normalize.csv",index="")