# How to build and run from source with docker

## Prerequisites
In order to download necessary tools, clone the repository, you need network access.

You'll need the following tools:
- [GIT](https://git-scm.com/)
- [Docker](https://www.docker.com/)

## Build and Run
### Getting the sourcees
<!-- TODO: forkの方法に修正する。 -->
First, fork the repository.
```
git clone https://github.com/<<<your-github-account>>>/LexicalTranslationCounter.git
```

If you want to pull new changes to your fork, execute the command below.
```
cd LexicalTranslationCounter
git checkout main
git pull https://github.com/media-of-langue/LexicalTranslationCounter.git main
```

### Build
Build development container using docker.
"sudo" is sometimes required.
lang_a and lang_b are language codes, and their order should be determined alphabetically.

```
docker-compose build --build-arg "lang_a={lang_a}" --build-arg "lang_b={lang_b}" --build-arg "tag_wordlist={tag_wordlist}" --build-arg "tag_corpus={tag_corpus}" && docker compose up -d
```
ex:
```
docker-compose build --build-arg "lang_a=en" --build-arg "lang_b=ja" --build-arg "tag_wordlist=latest" --build-arg "tag_corpus=latest" && docker compose up -d
```
```
docker-compose build --build-arg "LANG_A=en" --build-arg "LANG_B=ja" --build-arg "TAG_WORDLIST=v2" --build-arg "TAG_CORPUS=compact" && docker compose up -d
```

### Enter Container
Enter container.
```
docker-compose exec ltc /bin/bash
```

### Run count_function
Prepare the following files in /root/src/data/input/.
If the language is already supported, it will be pulled from the docker image when you build.

Check carefully as notes for each language and language-to-language when executing may be found in the language code folder of the document.

See [File Reference](File_reference.md) for file contents.
- corpus_{lang_a}_{lang_b}.csv
- wordlist_{la}_{pos}.csv

Execute count function.
The results are stored in /root/src/data/output/.
```
cd /root/src/
python3 count_function.py {lang_a} {lang_b} 0
```
ex: before running below command, you should prepare model files in /root/src/model/model_without_co. See [Readme.md for en-ja](documents/en-ja/Readme.md) for details.
```
python3 count_function.py en ja 0
```

If you are interrupted by an error on the way, run with the first argument being the value in /root/src/data/output/passed_id.txt plus one.

### Check the outputs
You can upload your relations and check the results by uploading your local data from the side menu of [media of langue](http://media-of-langue.org/)
