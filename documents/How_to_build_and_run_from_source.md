# How to build and run from source

## Prerequisites
In order to download necessary tools, clone the repository, you need network access.

For Docker-based runs, you'll need the following tools:
- [GIT](https://git-scm.com/)
- [Docker](https://www.docker.com/)

For the Release asset path, you can skip Docker if you already have a local
Python environment with the language-pair dependencies installed.

## Build and Run
### Getting the sources
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

### Build the container
Build the development container for the language pair you want to run. You can
skip this Docker step if you only want to use the Release asset from a local
Python environment.
"sudo" is sometimes required.
`la1` and `la2` are language codes, and their order should be determined
alphabetically.

```
docker-compose build --build-arg "LA1={la1}" --build-arg "LA2={la2}" && docker compose up -d
```
```
ex:
docker-compose build --build-arg "LA1=en" --build-arg "LA2=ja" && docker compose up -d
```

### Enter Container
Enter container.
```
docker-compose exec ltc bash
```

### Choose input data

There are three practical input sizes. Choose the smallest one that matches your
purpose. The tracked test-data and Docker-data examples below are run inside the
Docker container. The Release asset example is run from the host repository root
because it is the path that avoids downloading the Docker corpus image.

#### 1. Tracked test data: quick operation check

Use the files committed under `src/test/data/` when you only want to confirm
that the code path runs. These files are intentionally tiny and are not suitable
for graph quality checks or alignment experiments.

Example for the tracked `en-fr` fixture:

```
cd /root/src/
python3 count_function.py 0 en fr \
  --input-dir ./test/data \
  --output-dir ./test/result_of_test/count_function_en_fr \
  --max-rows 20
```

#### 2. Release asset data: small alignment experiment

Use the de-en sample corpus distributed as a GitHub Release asset when you want
to do a small but more realistic alignment experiment without downloading the
full Docker data. The fetch helper installs it under
`src/data/samples/de_en/`.

Run this from the repository root on the host machine. If you run
`count_function.py` outside Docker, your local Python environment must have the
same language-pair dependencies as the Docker image.

```
python3 scripts/fetch_sample_data.py --force

cd src
python3 count_function.py 0 de en \
  --input-dir ./data/samples/de_en/input \
  --max-rows 1000
```

The asset is useful for local development because it is much larger than the
tracked test fixture, but still small enough to fetch quickly.

#### 3. Docker data: full run

Use the default Docker data path for full-scale runs. Prepare the following
files in `/root/src/data/input/`. If the language pair is already supported,
the data is pulled during the Docker build.

Check carefully as notes for each language and language-to-language when executing may be found in the language code folder of the document.

See [File Reference](File_reference.md) for file contents.
- corpus_{la1}_{la2}.csv
- wordlist_{la}_{pos_tag}.csv

Execute count function.
The results are stored in /root/src/data/output/.
```
cd /root/src/
python3 count_function.py 0 {la1} {la2}
```
```
ex: 
python3 count_function.py 0 en fr
```

For development runs, you can limit the number of rows and point to any input
directory:
```
python3 count_function.py 0 de en \
  --input-dir ./data/input \
  --output-dir ./data/output \
  --max-rows 1000
```

At the end of every run, `count_function.py` prints a short timing summary:
total time, model load/setup time, processing time, processing time per
sentence, and processed sentence count. The detailed timing JSON is also written
to `timing_{la1}_{la2}.json` in the output directory.

If you are interrupted by an error on the way, run with the first argument being the value in /root/src/data/output/passed_id.txt plus one.

### Maintainer: build a local de-en sample package

For maintainers with local de-en source data, the helper below builds a small
raw input package. It uses full LTC relations only to choose graph-friendly
corpus rows; the packaged data itself is raw input files under `src/data/input/`.

```
python3 scripts/build_sample_corpus.py --force
```

Default output:

- `../de-en/samples/ltc-sample-de-en-small/`
- `../de-en/samples/ltc-sample-de-en-small.tar.zst`

### Check the outputs
You can upload your relations and check the results by uploading your local data from the side menu of [media of langue](http://media-of-langue.org/)
