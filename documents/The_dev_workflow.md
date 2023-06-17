# The development workflow

## Getting the sourcees
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

## Build
Build development container using docker.

"sudo" may be required.

la1 and la2 are language codes, and their order should be determined alphabetically.
```
cd floats_count_function
cp .env.example .env
cd exec_envs/basis
docker-compose build --build-arg "LA1={la1}" --build-arg "LA2={la2}" && docker compose up -d
```

## Enter Container
Enter container.

```
docker-compose exec cnt_func bash
```
## Update or add languages and interlanguage relations
Check carefully as notes for each language and language-to-language when executing may be found in the language code folder of the document.

Update the functions or add the data.
Please check 
- [Add language](Add_language.md)
- [Add language pair](Add_language_pair.md)
- [Update or Add functions](Update_or_Add_functions.md)
- [Update or Add data](Update_or_Add_data.md)

## Test 
Follow the documentation in [How to test](How_to_test.md) to see how each function works.
The results of this test will also be included in the pull request and used by reviewers to check its accuracy.

## Pull Requests

To enable us to quickly review and accept your pull requests, always create one pull request per issue and link the issue in the pull request. Never merge multiple requests in one unless they have the same root cause.  Avoid pure formatting changes to code that has not been modified otherwise.

## Merge main branch and floats

We or the other contributor check your accuracy of your pull requests and merge them to main branch and floats.

Then, you can feel the change on the web site, floats.org.
