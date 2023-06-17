# Add language pair

You can add relations between 2 languages which exit.

This document describe the way to add language pair.

If there isn't language you want to add, please follow [Add language](Add_language.md) to add languages.

## Check it works

Please refer to [How_to_build_and_run_from_source](How_to_build_and_run_from_source.md) to see the actual code in action.

## Add shellscripts for building docker container
Create an inter-language folder in the shell_scripts directory with the language codes connected, and create install.sh and requirements.txt in it. These will be executed at build time.

If there are libraries that cannot be installed during this language-specific docker build or information that needs to be communicated to the next developer, create a folder in the documens folder with a name that connects the language codes between the languages and create a Readme file there.

## Add corpus data and relations table

Please check the [Update or Add data](Update_or_Add_data.md) add the corpus test data set.

## Add alignment function 

Develop alignment function with reference to [Update or Add functions](Update_or_Add_functions.md).

Here the order of languages should be consistent with the alphabetical order of language codes.
