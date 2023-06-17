# Add language

This document describes how to add languages.

If the language you wish to add already exists, please follow [Add language pair](Add_language_pair.md) to describe the relationship between the languages.

## Check it works

Please refer to the [How_to_build_and_run_from_source](How_to_build_and_run_from_source.md) to actually run the code.

## Add shellscripts for building docker container
Create a language code folder in the shell_scripts directory and create install.sh and requirements.txt in it. These will be executed during build.

If there are libraries that cannot be installed during this language-specific docker build or information that needs to be communicated to the next developer, create a folder in the documens folder with a name that language code and create a Readme file there.

## Add wordlist data

Add the wordlist data with reference to [Update or Add data](Update_or_Add_data.md).

Send this data to us by [form](https://forms.gle/LmWz8DYAc1C9xoRV6) at the same time.


## Add normalize function and morphological function

Please refer to the [Update or Add functions](Update_or_Add_functions.md) to develop normalize function and morphological function.

Be sure to run through the test and output the results.

This output will be included in the pull request and will be available for review by other contributors.

## Add language pair

We are grateful enough at this point, but we encourage you to add language pairs as well.

[Add language pair](Add_language_pair.md)
