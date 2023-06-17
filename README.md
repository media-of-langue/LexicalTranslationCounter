# Count function for "Media of Langue"

## The Repository

This repository provides ”Count Function” to produce the material for "[Media of Langue](http://www.media-of-langue.org)".

This function counts and writes down ’That word was translated into this word’ from the accumulation of translation activities between any two languages.

In other words, this function has the following inputs and outputs:

- **Input**：bilingual corpus and wordlist
- **Output**：Table that stores the number of times a word (language 1) is translated into a word (language 2)



## Construction

Count function works by calling the following three functions.

- **Alignment function**：Function to figure out which words correspond to which words in a translated sentence pair
- **Normalize function**：Functions to link multiple expressions and conjugations of a word to a single representative word
- **Morphological function(Option)**：Functions to split sentences into words and determine word class. This function is sometimes included in Alignment function.

The Alignment function exists for interlanguage (e.p. English-French), while the Normalize function and Morphological function exist for a single language (e.p. Japanese).
There is room for improvement in these functions at present, and we welcome contributors who can improve them together.
You can also easily create the data abot new language and new inter-language that have not yet been introduced to “Media of Langue" by duplicating and modifying these functions.




## Media of Langue
![Image 2022-10-14 at 17 32](https://user-images.githubusercontent.com/52962800/195801348-232aecdd-b21f-4654-839c-12da43712806.jpg)

Media of Langue is a map of several spaces drawn by the myriad of translations that take place.
<!--floatsの単語間のつながりのデータはcount functionが更新されるタイミングや、データが更新されるタイミングでことによって徐々に書き換えられていきます。-->
To view Media of Langue, go to http://www.media-of-langue.org.

## Contributing


- Update or launch "alignment function"
  - This function can be created for two languages for which "Normalize function" and "Morphological function" have already been created. Counting up the output of this function completes the material that make up the Media of Langue diagram. We hope that in the future this function will be created for all languages for which there are enough corpora in the world.

- Update or launch "Normalize function" or "Morphological function"
  - These functions exist for each language, so improving them involves improving the behavior across all the language-pair the language involves. We are willing to use existing tools.

- Review PullRequest
  - We would appreciate a review of the accuracy of the proposed improvements to "Count function". Since the managers are familiar to few languages, this help would be a great contribution to the evaluation of their accuracy.

- Suggestions for databases
  - You can suggest a more appropriate bilingual corpus for a given language pair, or a more appropriate word list for a given language or part of speech.

- Criticism, critique, and advice on projects
  - Each part of Media of Langue contains multiple non-trivial judgments about language, translation, meaning, and perception. We believe that all of them should be open to ongoing criticism.


If you are interested in fixing issues and contributing directly to the code base, please see the following:


- [How to build and run from source](documents/How_to_build_and_run_from_source.md)
- [The development workflow](documents/The_dev_workflow.md)
- [Add language pair](documents/Add_language_pair.md)
- [Add language](documents/Add_language.md)
- [Update or Add Functions](documents/Update_or_Add_funtions.md)
- [Update or Add Database](documents/Update_or_Add_data.md)
- [How to test](documents/How_to_test.md)
- [File reference](documents/File_reference.md)

## Feedback

Please feel free to contact us if you have any inquiries. 

media.of.langue@gmail.com

## Development Container

You can easily prepare an environment for development using Docker.
Of course, it can be executed in any environment, including local, by following the appropriate procedures.

See ”How to build and run from source” in the documents directory for details.

