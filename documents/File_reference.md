# File Reference

## Files

- count_function.py
- alignment.py
- {lang}_normalizer.py
- {lang}_morphological.py
- corpus_{lang_a}_{lang_b}.csv
- wordlist_{lang}_{pos}.csv
- translangtions_{lang_a}\_{lang_b}\_{pos}.csv

`lang_a` and `lang_b` are language codes, and their order should be alphabetical.

There are four poses: adj, adverb, noun, and verb.

## count_function.py

This file is used to run the entire process.
```
count_function.py {offset} {lang_a} {lang_b}

input file: 
/root/src/data/input/corpus_{lang_a}_{lang_b}.csv
/root/src/data/input/wordlist_{lang_a}_{pos}.csv
/root/src/data/input/wordlist_{lang_b}_{pos}.csv

output file:
/root/src/data/output/translations_{lang_a}_{lang_b}_{pos}.csv
/root/src/data/input/corpus_{lang_a}_{lang_b}.csv
```

## alignment.py

Execute corpus alignment.
It exists in /root/src/alignment/{lang_a}_{lang_b}/ for each language.
This file contains the following functions

```
alignment(corpus_row,wordlist,test=false)
return 
[
	{
		"pos":{pos},
		"id_translation":{id},
		"id_{lang_a}":{id},
		"word_{lang_a}":{word},
		"id_{lang_b}":{id},
		"word_{lang_b}":{word}
	}
]
```

## normalizer.py

Contains a function that performs normalization of word orthography.
It exists in /root/src/normalizer/ under the name {lang}_normalizer.py.

```
{lang}_normalizer(word, pos, wordlist, test=False)

retuern id, word_normalized
```

## morphological.py

It contains functions for word tokenization and morphological analysis.
It exists in /root/src/morphological/ under the name {lang}_morphological.py.
This function is not necessarily present in all languages and can be located in an alignment file, but it is recommended that it be created so that it can be used commonly across languages.

```
{lang}_morphological.py(sentence)

return tokenized, mrph
```

## corpus
A corpus exists for each interlanguage.
A list of corpus sources can be found at [Used dataset list](./Acknowledgements/Used_dataset_list.md).
### columns

The corpus is composed of the following columns

| columns             | describe                |
|---------------------|-------------------------|
| id                  | id of the corpus:SERIAL |
| sentence_{lang_a}   | sentence of lang_a:Text |
| sentence_{lang_b}   | sentence of lang_b:Text |
| alignment_info      | result of align:Array   |

## wordlist
A wordlist exists for each part of speech for each language.

These are the output of the normalize function and indicate the words that may appear.

### columns

The wordlist consists of the following columns.

| column  | describe              |
|---------|-----------------------|
| id_word | id of the word:SERIAL |
| name    | word_normalized:Text  |

## translations

Translations exist for each interlanguage and are added for each new word pair found in the corpus that is translated.

### columns

The translations are composed of the following columns. This table is created using the alignment functions in this repository to configure the production environment.

| columns        | describe                                           |
|----------------|----------------------------------------------------|
| id_translation | id of the translation:SERIAL                       |
| id_{lang_a}    | id of lang_a:Integer                               |
| id_{lang_b}    | id of lang_b:Integer                               |
| id_corpus_list | array of id_corpus the translations detected:Array |
