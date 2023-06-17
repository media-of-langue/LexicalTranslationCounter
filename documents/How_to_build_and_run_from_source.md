# How to build and run from source with docker

## Prerequisites
In order to download necessary tools, clone the repository, you need network access.

You'll need the following tools:
- [GIT](https://git-scm.com/)
- [Docker](https://www.docker.com/)

## Build and Run
### Getting the sourcees
First, fork the repository.
```
git clone https://github.com/<<<your-github-account>>>/floats_count_function.git
```

If you want to pull new changes to your fork, execute the command below.
```
cd floats_count_function
git checkout main
git pull https://github.com/floats01/count_function.git main
```

### Build
Build development container using docker.
"sudo" is sometimes required.
la1 and la2 are language codes, and their order should be determined alphabetically.

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
docker-compose exec cnt_func bash
```

### Run count_function
Prepare the following files in /root/src/data/input/.
If the language is already supported, it will be pulled from the docker image when you build.

Check carefully as notes for each language and language-to-language when executing may be found in the language code folder of the document.

See [File Reference](File_reference.md) for file contents.
- corpus_{la1}_{la2}.csv
- wordlist_{la}_{pos_tag}.csv

Execute count function.
The results are stored in /root/src/data/input/.
```
cd /root/src/
python3 count_fuction.py 0 {la1} {la2}
```
```
ex: 
python3 count_fuction.py 0 en fr
```

If you are interrupted by an error on the way, run with the first argument being the number of corpora already processed or the value in /root/src/data/output/passed_id.txt plus one.

### Check the outputs
You can upload your relations and check the results by uploading your local data from the side menu of[media of langue](http://media-of-langue.org/)
