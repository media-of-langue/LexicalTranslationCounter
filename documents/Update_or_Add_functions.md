# Update and Add Functions

## workflow
Reffer [The development workflow](The_dev_workflow.md).

## Update Function

change the functions with this reference and make pull request.

## Add Function

When you add new language or language pair, you should add the functions below.

Create a new language or interlanguage function to be added by copying a function from another language or interlanguage. In principle, the following functions should be edited when adding a language or interlanguage.

language：normalize function, morphological function

interlanguage：alignment function

In addition to the functions, it is also necessary to add a data set. See [Update and Add Data](Update_and_Add_data.md) for more information on this.


## Normalize Function

This function is used to align the notations of words that have multiple notations, such as conjugations, into a single notation.

In the production database, all words are passed through the latest version of this function, which is also applied to all counting functions and queries from the front end.

This function exists in '/root/src/normalizer/' for each language.

### Input and Output
Returns the word that normalize input word and the id of the word on the pos_tag.
```
{la}_normalizer(word, pos_tag, wordlist, test=False)
retuern id, word_normalized
```
```
ex)
en_normalizer("played", "v", wordlist)
output: 36, play
```

### Test the function
Run normalize_test.py in '/root/src/test/', specifying the language.

The result of normalizing wordlist is returned.

By default, the test mode is set to True and the word id is not returned.
```
cd /root/src/test/
python3 normalizer_test.py {la}
```
```
ex)
python3 normalizer_test.py en
```

The results are output to /root/src/test/result_of_test/ by part-of-speech in the following format.

However, this file only outputs the forms and words in the wordlist that change.
```
word_origin->normalized_word

ex)
plays->play
```

## Alignment Function

This function is used to align words in the corpus.

This function is located in '/root/src/alignment/' for each language.

### Input and Output
Returns the result of alignment.
```
alignment(corpus_row,wordlist,test=false)

return [[{pos_code},{word_la1_id},{word_la1},{word_la2_id},{word_la2}], ]
```
```
ex)
alignment([0,"you are beautiful","あなたは美しい",[],False],wordlist)
output: [["n",30,"you",12,"あなた"],["a",1,"beautiful",2,"美しい"]]
```

### Test the function
Run alignment_test.py in '/root/src/test/', specifying the language.

The result of aligning the corpus of test data will be output.

```
cd /root/src/test/
python3 alignment_test.py {la1} {la2}
```
The results are output to /root/src/test/result_of_test/ in the following format.
```
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
old align
word_A - word_a
new align
word_A - word_a word_B - word_b

ex:
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
old align

new align
Resumption - Reprise  session - session  
```


## Morphological Functions

Morphological Functions exists for each languages and in '/root/src/morphological/'
The purpose of this function is to divide a sentence into words and identify the part of speech of each word in the sentence.
It is permitted to write this function directly into the alignment function, and although it does not have to be created, it is recommended that it is cut out as a function as it can be shared between multiple languages to reduce man-hours for other developers.

### Input and Outputs
Returns the word list and pos tag list of the input sentence.
input: sentence
output: word list, pos tag list
```
{la}_morphological.py(sentence)

return tokenized, mrph
```
```
ex)
en_morphological("you are beautiful")
output: ["you","are","beautiful"],["n","v","a"]
```

### Test the function
Run morphological_test.py in '/root/src/test/' specifying two languages, including the newly created language. In principle, the other language should be English, and the test can be run with the other language only if there is no test corpus available for English.

Morphological analysis results of the sentences in the corpus are output.

If you want to try it on a specific sentence, please modify the code directly.
```
cd /root/src/test/
python3 morphological_test.py {la1} {la2}
```

```
ex) python3 morphological_test.py en fr
```

結果が下記のフォーマットで /root/src/test/result_of_test/ に出力されます。
```
word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1
word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2
```
```
ex)
Resumption:n of:N/A the:N/A session:n 
Reprise:n de:N/A la:N/A session:n 
```