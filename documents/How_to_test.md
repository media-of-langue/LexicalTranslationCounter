# How to test

## prepare test data
Place the following test data in `src/test/data/`. For the file format, refer to [File Reference](File_reference.md).

The number of lines of corpus test data should not exceed 100 lines

- corpus_{la1}_{la2}.csv
- wordlist_{la}_{pos_tag}.csv

`src/test/data/` contains the tracked fixtures. Test outputs are generated under `src/test/result_of_test/` and are intentionally not tracked.

## alignment function
The result of aligning the corpus of test data is output.

```
ROOT=$(pwd) .venv/bin/python src/test/alignment_test.py {la1} {la2}
```
The results are output to `src/test/result_of_test/` in the following format.
```
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
word_A - word_a word_B - word_b

ex:
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
Resumption - Reprise  session - session  
```

You can also test for a single sentence pair.
Please specify the sentences for sentence_la1 and sentence_la2 in the code.

```
ROOT=$(pwd) .venv/bin/python src/test/alignment_test_single.py {la1} {la2}
```
The results are output to the console in the following format.
```
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
word_A - word_a word_B - word_b

ex:
sentece_la1:Resumption of the session
sentece_la2:Reprise de la session
new align
Resumption - Reprise  session - session  
```

## normalize function
It returns the result of normalizing a word based on its part-of-speech.

By default, the test mode is set to True and the word id is not returned.
```
ROOT=$(pwd) .venv/bin/python src/test/normalizer_test.py {la}
```
```
ex)
ROOT=$(pwd) .venv/bin/python src/test/normalizer_test.py en
```

The results are output to `src/test/result_of_test/` for each part of speech in the following format.
However, this file will only output the forms and words in wordlist that change.
```
word_origin->normalized_word

ex)
plays->play
```

You can also test with respect to a single word.
```
ROOT=$(pwd) .venv/bin/python src/test/normalizer_test_single.py {la} {word}
```
```
ex)
ROOT=$(pwd) .venv/bin/python src/test/normalizer_test_single.py en plays
```


## morphological function

Run `src/test/morphological_test.py`, specifying two languages including the newly created language. In principle, the other language should be English; use another language only if no English test corpus is available.

Morphological analysis results of the sentences in the corpus are output.

```
ROOT=$(pwd) .venv/bin/python src/test/morphological_test.py {la1} {la2}
```

```
ex) ROOT=$(pwd) .venv/bin/python src/test/morphological_test.py en fr
```

The results are output to `src/test/result_of_test/` in the following format.
```
word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1 word_la1:pos_tag_la1
word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2 word_la2:pos_tag_la2

ex)
Resumption:n of:N/A the:N/A session:n 
Reprise:n de:N/A la:N/A session:n 
```

A single sentence can also be tested.
Sentences should be specified by directly rewriting the sentences in the code.
```
ROOT=$(pwd) .venv/bin/python src/test/morphological_test_single.py {la}
```

```
ex) ROOT=$(pwd) .venv/bin/python src/test/morphological_test_single.py en
```

The results are displayed in the console in the following format.
```
word_la:pos_tag_la word_la:pos_tag_la word_la:pos_tag_la word_la:pos_tag_la

ex)
Resumption:n of:N/A the:N/A session:n 
```

## Check the outputs
You can check the test result in the console or in `src/test/result_of_test/`.
Use these outputs to check the behavior and accuracy of the code.
