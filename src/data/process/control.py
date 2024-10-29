from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController
import time
import pyautogui
import pyperclip
import pandas as pd
import os
import chardet
import glob
import re
os.chdir(os.path.dirname(__file__))

mouse = MouseController()
keyboard = KeyboardController()
skip=True
break_word=""
if break_word=="":
    skip=False
time.sleep(1)
test=False

langs=["it","en","de"]
pos_tags=["adj","noun","verb","adverb"]
button_names=["send","input",]
home_dir="."
subject_path=f"{home_dir}/datas"
input_path=f"{subject_path}/input"
os.makedirs(subject_path,exist_ok=True)
os.makedirs(input_path,exist_ok=True)


langs=["it","en","de"]
pos_tags=["adj","noun","verb","adverb"]
base_exp="csv"
wordlist="wordlist_"

def extract_tail(save_path,lang_id,pos_tag_id,tail,delete=False,load_exp=base_exp,base_name=wordlist):
    target =data_downloader(f"{home_dir}/{base_name}{langs[lang_id]}_{pos_tags[pos_tag_id]}.{load_exp}")
    bool_seriese=target.apply(lambda x:False==delete if str(x)[-1] in tail else True==delete)
    
    data=target[bool_seriese]
    if test:
        data=data.iloc[:100]
    match os.path.splitext(os.path.basename(save_path))[-1][1:]:
        case "csv":data.to_csv(save_path)
        case "xlsx":data.to_excel(save_path)
        case "pickle":data.to_pickle(save_path)

def data_downloader(openfile):
    encoding=""
    with open(openfile, 'rb') as f:
        result = chardet.detect(f.read())
        encoding=result["encoding"]
    data=pd.read_parquet(openfile)
    data=data.iloc[:,0]
    return data

def get_place(button_name,wait_time=5):
    print(f"please touch {button_name} in {str(wait_time)} seconds")
    time.sleep(wait_time)
    x, y = pyautogui.position()
    print(f"x:{x},y:{y}")
    return x,y

def first_setting(button_names):
    button_place_dict={}
    for button_name in button_names:
        x,y=get_place(button_name=button_name)
        button_place_dict[button_name]=(x,y)
    return button_place_dict
        
def input_string(string,button_place_dict,absolute=False):
    global skip
    global break_word
    if re.match(break_word,string):
        skip=False
    if (not skip) or absolute :
        click_button(1,button_place_dict)
        click_button(1,button_place_dict)
        time.sleep(0.1)
        texts=re.split("\n",string)
        for text in texts:
            pyautogui.write(text,interval=0.05)
            pyautogui.hotkey("shift","enter")
        time.sleep(1)
        click_button(0,button_place_dict)
    
    
def click_button(button_id,button_place_dict):
    button_place=button_place_dict[button_names[button_id]]
    pyautogui.moveTo(button_place[0],button_place[1], duration=0.01)
    pyautogui.click()
    

def batch_make(data,size=200):
    data_list=[]
    n=0
    text=""
    for row in data:
        text=f"{text}{str(row)}\n"
        n+=1
        if n%size==0:
            data_list.append(text)
            text=""
    data_list.append(text)
    return data_list

def copy_all_the_page():
    def press_with_command(key):
        pyautogui.keyDown('command')   # または 'cmd' としても可
        pyautogui.press(key)
        pyautogui.keyUp('command')
        time.sleep(1)
    press_with_command("a")
    press_with_command("c")
    time.sleep(5)
    copied_text = pyperclip.paste()
    return copied_text

def get_target_word_list(target_column):
    target_word_list=[]
    page_text=copy_all_the_page()
    page_text=re.split("\n",page_text)
    for page_row in page_text:
        if re.fullmatch(f".+ 	{target_column}",page_row):
            target_word_list.append(re.split(" 	",page_row)[0])
    return target_word_list

def question(input_str,data,button_place_dict):
    input_string(input_str,button_place_dict,absolute=True)
    time.sleep(3)
    data=batch_make(data)
    for text in data:
        input_string(text,button_place_dict)
        if not skip:
            time.sleep(20)

def go_to_next_GPT(button_place_dict):
    for num in [2,3]:
        click_button(num,button_place_dict)
        time.sleep(0.5)

"""
def main():
    button_place_dict=first_setting(button_names)
    print(button_place_dict)

    judge_dict={
        #"plural or Singular":[1,["i","e"],False],
        "Past tense or present tense":[2,[],True],
        "Past tense or present tense":[0,[],True],
        "plural or Singular":[0,[],True],
        
        
    }
    for judge,config in judge_dict.items():
        judge_=re.sub(" ","_",judge)
        target_column=re.split(" or ",judge)[0]
        openfile=f"{input_path}/{judge_}.{base_exp}"
        extract_tail(openfile,0,config[0],config[1],delete=config[2])
        data=data_downloader(openfile)
        input_str=f"You want to provide Italian words and have them classified as {judge}, then returned in a table format."
        question(input_str,data,button_place_dict)
        time.sleep(50)

        target_word_list=get_target_word_list(target_column)
        go_to_next_GPT(button_place_dict)
        input_str=f"Please convert the following list of Italian words from {re.sub(" or "," to ",judge)} and output them in a table format."
        question(input_str,target_word_list,button_place_dict)

  """  


def main():

    
    data=data_downloader("past.parquet")
    data=batch_make(data)
    print(data)
    button_place_dict=first_setting(button_names)
    skip=False
    click_button(0,button_place_dict)
    click_button(0,button_place_dict)
    input_string(f"please change these past tense words to original word and make a table",button_place_dict)
    
   
    for text in data:
        input_string(text,button_place_dict)
        if not skip:
            time.sleep(20)
if __name__=="__main__":
    main()