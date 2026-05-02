# How to build and run from source

## Prerequisites

Clone the repository first. The lightweight de-en path does not require Docker.

For lightweight local de-en runs:

- [Git](https://git-scm.com/)
- Python 3 with `venv`
- Network access for Python packages, spaCy/NLTK resources, and the sample data
  Release asset
- The awesome-align model, downloaded manually as described in
  [documents/de-en/Readme.md](de-en/Readme.md)

For full Docker runs:

- [Docker](https://www.docker.com/)

The Docker build path pulls the full corpus and wordlist Docker images. Use it
only when you need the full data.

## Getting the sources

First, fork the repository.

```
git clone https://github.com/<<<your-github-account>>>/LexicalTranslationCounter.git
cd LexicalTranslationCounter
```

If you want to pull new changes to your fork, execute the command below.

```
git checkout main
git pull https://github.com/media-of-langue/LexicalTranslationCounter.git main
```

## Lightweight local de-en run

This path is intended for quick operation checks and small alignment
experiments. It does not build the Docker image and does not pull the full
corpus Docker image.

### Set up the local runtime

The helper below creates `.venv`, installs the de-en Python dependencies,
downloads the spaCy/NLTK resources, and checks that the manually downloaded
awesome-align model is present.

```
python3 scripts/setup_local_runtime.py --language-pair de-en
```

If the helper reports missing files under `src/model/awesome_model_with_co/`,
follow [documents/de-en/Readme.md](de-en/Readme.md), place the model files, and
run:

```
python3 scripts/setup_local_runtime.py --language-pair de-en --check-only
```

### 1. Tracked test data: quick operation check

Use `src/test/data/` when you only want to confirm that the de-en code path
runs. These files are intentionally tiny and are not suitable for graph quality
checks.

```
ROOT=$(pwd) .venv/bin/python src/test/morphological_test.py de en
ROOT=$(pwd) .venv/bin/python src/test/alignment_test.py de en
```

The outputs are written under `src/test/result_of_test/`.

### 2. Release asset data: small alignment experiment

Use the de-en sample corpus distributed as a GitHub Release asset when you want
to run `count_function.py` on a small but more realistic input set. The fetch
helper installs it under `src/data/samples/de_en/`.

```
python3 scripts/fetch_sample_data.py --force

ROOT=$(pwd) .venv/bin/python src/count_function.py 0 de en \
  --input-dir src/data/samples/de_en/input \
  --output-dir src/data/output/de_en_sample \
  --max-rows 1000
```

The asset is useful for local development because it is much larger than the
tracked test fixture, but still small enough to fetch quickly.

At the end of every `count_function.py` run, it prints a short timing summary:
total time, model load/setup time, processing time, processing time per
sentence, and processed sentence count. The detailed timing JSON is also written
to `timing_{la1}_{la2}.json` in the output directory.

## Full Docker run

Use this path when you need the full corpus and wordlists. The Docker build
pulls `mediaoflangue/wordlist_*` and `mediaoflangue/corpus_*` images for the
requested language pair.

`la1` and `la2` are language codes, and their order should be determined
alphabetically. `"sudo"` is sometimes required.

```
docker-compose build --build-arg "LA1={la1}" --build-arg "LA2={la2}" && docker compose up -d
```

Example:

```
docker-compose build --build-arg "LA1=en" --build-arg "LA2=ja" && docker compose up -d
```

Enter the container.

```
docker-compose exec ltc bash
```

Prepare the following files in `/root/src/data/input/`. If the language pair is
already supported, these files are copied from the pulled Docker data images
during the Docker build.

See [File Reference](File_reference.md) for file contents.

- `corpus_{la1}_{la2}.csv`
- `wordlist_{la}_{pos_tag}.csv`

Execute count function. The results are stored in `/root/src/data/output/`.

```
cd /root/src/
python3 count_function.py 0 {la1} {la2}
```

Example:

```
python3 count_function.py 0 en fr
```

For development runs inside Docker, you can limit the number of rows and point
to any input directory:

```
python3 count_function.py 0 de en \
  --input-dir ./data/input \
  --output-dir ./data/output \
  --max-rows 1000
```

If you are interrupted by an error on the way, run with the first argument being
the value in `/root/src/data/output/passed_id.txt` plus one.

## Maintainer: build a local de-en sample package

For maintainers with local de-en source data, the helper below builds a small
raw input package. It uses full LTC relations only to choose graph-friendly
corpus rows; the packaged data itself is raw input files under `src/data/input/`.

```
python3 scripts/build_sample_corpus.py --force
```

Default output:

- `../de-en/samples/ltc-sample-de-en-small/`
- `../de-en/samples/ltc-sample-de-en-small.tar.zst`

## Check the outputs

You can upload your relations and check the results by uploading your local data
from the side menu of [Media of Langue](http://media-of-langue.org/).
