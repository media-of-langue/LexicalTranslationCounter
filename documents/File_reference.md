# File Reference

## Files

- count_function.py
- alignment.py
- {la}_normalizer.py
- {la}_morphological.py
- corpus_{la1}_{la2}.csv
- wordlist_{la}_{pos_tag}.csv
- relations_{la1}\_{la2}\_{pos_tag}.csv

la1 and la2 are language codes, and their order should be alphabetical
There are four pos_tags: adj, noun, verb, and adverb.

## count_function.py

This file is used to run the entire process.
```
count_function.py {offset} {la1} {la2}

input file: 
/root/src/data/input/corput_{la1}_{la2}.csv
/root/src/data/input/wordlist_{la1}_{pos_tag}.csv
/root/src/data/input/wordlist_{la2}_{pos_tag}.csv

output file:
/root/src/data/output/relations_{la1}_{la2}_{pos_tag}.csv
/root/src/data/input/corput_{la1}_{la2}.csv
```

## alignment.py

Execute corpus alignment.
It exists in /root/src/alignment/{la1}_{la2}/ for each language.
This file contains the following functions

```
alignment(corpus_row,wordlist,test=false)

return [[{pos_code},{word_la1_id},{word_la1},{word_la2_id},{word_la2}], ]
```

## normalizer.py

Contains a function that performs normalization of word orthography.
It exists in /root/src/normalizer/ under the name {la}_normalizer.py.

```
{la}_normalizer(word, pos_tag, wordlist, test=False)

retuern id, word_normalized
```

## morphological.py

It contains functions for word tokenization and morphological analysis.
It exists in /root/src/morphological/ under the name {la}_morphological.py.
This function is not necessarily present in all languages and can be located in an alignment file, but it is recommended that it be created so that it can be used commonly across languages.

```
{la}_morphological.py(sentence)

return tokenized, mrph
```

## corpus
A corpus exists for each interlanguage.

Floats are constructed by counting the number of times a word is translated in this corpus.

A list of corpus sources can be found at [aboutページ](http://localhost:5011/manual).
### columns

The corpus is composed of the following columns

| columns             | describe                |
|---------------------|-------------------------|
| id                  | id of the corpus:SERIAL |
| sentence_{la1} | sentence of la1:Text    |
| sentence_{la2} | sentence of la2:Text    |
| commands            | result of align:Array   |
| invalid             | invalid:Boolean         |

## wordlist
A wordlist exists for each part of speech for each language.

These are the output of the normalize function and indicate the words that may appear in the floats and their notation.

### columns

The wordlist consists of the following columns.

| column  | describe              |
|---------|-----------------------|
| id      | id of the word:SERIAL |
| word    | word_normalized:Text  |
| invalid | invalid:boolean       | 

## relations

Relations exist for each interlanguage and are added for each new word pair found in the corpus that is translated.

### columns

The relations are composed of the following columns. This table is created using the alignment functions in this repository to configure the production environment.

| columns     | describe                                        |
|-------------|-------------------------------------------------|
| id          | id of the relation:SERIAL                       |
| id_word_la1 | id of la1:Integer                               |
| id_word_la2 | id of la2:Integer                               |
| id_examples | array of corpus id the relations detected:Array |
| invalid     | invalid:Boolean                                 |
