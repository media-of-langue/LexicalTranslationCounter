# How to build and run from source

## Overview

Lexical Translation Counter supports multiple language pairs. Each language pair
can have different Python dependencies, NLP models, and notes. Check the
language-pair document under `documents/{la1}-{la2}/` when you work on a
specific pair.

There are two runtime paths:

- Local Python runtime: useful for quick checks and small experiments. This does
  not pull the full corpus Docker images.
- Docker runtime: useful for full runs. The Docker build pulls the full
  `mediaoflangue/wordlist_*` and `mediaoflangue/corpus_*` images for the
  selected language pair.

For a first try, start with the local Python runtime and the smallest useful
data. Use Docker only when you need the full data.

## Data Options

### 1. Tracked test data

`src/test/data/` contains tiny fixtures committed to Git. Use these files for
basic operation checks while developing a language pair.

This data is intentionally small. It is not suitable for checking graph quality
or realistic alignment behavior.

### 2. Release asset sample data

GitHub Release assets can provide small but more realistic sample corpora. These
assets are intended for local alignment experiments without downloading the full
Docker corpus image.

Currently, de-en and en-ja sample assets are available. More language-pair
sample assets can be added in the future using the same approach.

### 3. Full Docker data

The full corpus and wordlists are distributed through Docker data images. These
are copied into `/root/src/data/input/` during the Docker build.

Use this path for full-scale runs. Do not use it as the first operation check,
because Docker build pulls the full data images.

## Getting the Sources

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

## Local Python Runtime

Use this path when you want to avoid pulling the full Docker data images.

You need:

- Python 3 with `venv`
- Network access for Python packages and NLP resources
- The language-pair model files described in `documents/{la1}-{la2}/Readme.md`

### Example: de-en

The repository includes a setup helper for small local runs. It creates
`.venv`, installs the requested language-pair Python dependencies, downloads
NLTK resources, and checks that the manually downloaded awesome-align model is
present. Some language pairs have extra local tools; for example, en-ja also
requires `jumanpp` on `PATH`.

First, follow [documents/de-en/Readme.md](de-en/Readme.md) and place the model
under `src/model/awesome_model_with_co/`.

Then run:

```
python3 scripts/setup_local_runtime.py --language-pair de-en
```

If you have already installed the dependencies and only want to check the
environment:

```
python3 scripts/setup_local_runtime.py --language-pair de-en --check-only
```

### Tracked test data example

Use the tracked test data when you only want to confirm that the code path runs.

```
ROOT=$(pwd) .venv/bin/python src/test/morphological_test.py de en
ROOT=$(pwd) .venv/bin/python src/test/alignment_test.py de en
```

The outputs are written under `src/test/result_of_test/`.

### Release asset example

Use a sample asset when you want to run `count_function.py` on a small but more
realistic input set.

```
python3 scripts/fetch_sample_data.py --language-pair de-en --force

ROOT=$(pwd) .venv/bin/python src/count_function.py 0 de en \
  --input-dir src/data/samples/de_en/input \
  --output-dir src/data/output/de_en_sample \
  --max-rows 1000
```

For en-ja, use `--language-pair en-ja` and follow
[documents/en-ja/Readme.md](en-ja/Readme.md) for the model and Juman++ setup.

At the end of every `count_function.py` run, it prints a short timing summary:
total time, model load/setup time, processing time, processing time per
sentence, and processed sentence count. The detailed timing JSON is also written
to `timing_{la1}_{la2}.json` in the output directory.

## Full Docker Runtime

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

## Maintainer: Build a Sample Asset

The helper below builds a sample asset from local source data. It uses full LTC
relations only to choose graph-friendly corpus rows; the packaged data itself is
raw input files under `src/data/input/`.

```
python3 scripts/build_sample_corpus.py --language-pair de-en --force
```

Example de-en output:

- `../de-en/samples/ltc-sample-de-en-small/`
- `../de-en/samples/ltc-sample-de-en-small.tar.zst`

Example en-ja output:

```
python3 scripts/build_sample_corpus.py --language-pair en-ja --force
```

- `../ltc-data/samples/ltc-sample-en-ja-small/`
- `../ltc-data/samples/ltc-sample-en-ja-small.tar.zst`

Future language-pair sample assets should follow the same separation: keep the
small raw input package as a Release asset, keep full data in the Docker data
images, and keep pair-specific runtime notes under `documents/{la1}-{la2}/`.

## Check the Outputs

You can upload your relations and check the results by uploading your local data
from the side menu of [Media of Langue](http://media-of-langue.org/).
