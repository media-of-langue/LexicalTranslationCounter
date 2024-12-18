# docker-compose

20241211-17:41

## docker compose

1. [github](https://github.com/media-of-langue/LexicalTranslationCounter)
2. [How to build and run from source with docker](https://github.com/media-of-langue/LexicalTranslationCounter/blob/main/documents/How_to_build_and_run_from_source.md)
3. docker-compose build --build-arg "LA1=en" --build-arg "LA2=it" && docker compose up -d
4. failed to solve: mediaoflangue/wordlist_it:latest: failed to resolve source metadata for docker.io/mediaoflangue/wordlist_it:latest: pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
5. docker search mediaoflangue/wordlist_it
6. 存在しないことがわかる
7. wordlistを作らないと
8. corpusも作らないと
9. corpusを彼方に移し、wordlistを作成
10. wordlistは適当埋めてしまって、それを引っ張ってくる
11. aaakmn/に自分は収めている
    1. Dockerfileの4,5行目を
    2. FROM mediaoflangue//wordlist_${LA2}:latest AS wordlist2
    3. FROM mediaoflangue//corpus_${LA1}_${LA2}:latest AS corpus
    4. から
    5. FROM aaakmn/wordlist_${LA2}:latest AS wordlist2
    6. FROM aaakmn/corpus_${LA1}_${LA2}:latest AS corpus
    7. に変更
12. error 12111803 発生
13. environment:を消した
14. version 行を docker-compose.yml から削除してください。
15. docker-compose build 中に mediaoflangue/wordlist_it:latest が見つからずに失敗しています。
16. validating /Users/komuramakoto/記録/MOL/LexicalTranslationCounter/docker-compose.yml: services.ltc.environment must be a mapping
17. environment内を消したのが問題、書き加えた
18. いまだ出てくるinstall関係の問題
    1. どのやつが問題か、一つずつ消して行う
        1. nltkだけにしてみた
        2. pyknpだけにした
           1. failed to solve: error committing n6z6rwovv71p6eaf62su6x6cz: write /var/lib/docker/buildkit/metadata_v2.db: input/output error
           2. 空き容量がない
           3. エラーその２
              1. 問題文
                 1. 15.19   404  Not Found [IP: 185.125.190.39 80]
                 2. 15.20 Fetched 6894 kB in 6s (1061 kB/s)
                 3. 15.20 E: Failed to fetch
                 4. 404  Not Found [IP: 185.125.190.39 80]
                 5. 15.20 E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?
                 6. ------
                 7. failed to solve: process "/bin/sh -c cd ./basis/ && sh ./install.sh" did not complete successfully: exit code: 100
                 8. myenvkomuramakoto@mitsumuramakotonoMacBook-Air ~/記録/MOL/LexicalTranslationCounter 
              2. 解決策
                  1. apt-get updateを書き込む
                  2. apt-cache policy libcurl3-gnutls をDockerfileに書き込む
                     1. 失敗
                     2. failed to solve: process "/bin/sh -c apt-get update -y &&     apt-get upgrade -y &&     apt-get install -y apt-cache policy libcurl3-gnutls    locales     lo
                  3. apt-get update --fix_missingにする
                     1. 通った
            　1. pyknpだけでも問題発生


           4. Building00
           5. docker:desktoplinux　failed to solve: write /var/lib/docker/buildkit/containerdmeta.db: input/output error
        3. django-environだけ
           1. 不可能
        4. konlpy
        5. どれを消そうが変わらない
    2. ```sudo apt-get updatesudo apt-get install -y \build-essential python3-dev python3-pip cython```を実行
        1. Geographic area: 6をyamlに追加
        2. ```ENV TZ=Asia/Tokyo\RUN apt-get update &&  apt-get install -y tzdata && \ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \dpkg-reconfigure -f noninteractive tzdata```を実行
           1. ```failed to solve: process "/bin/sh bashrc" did not complete successfully: exit code: 100```
           2. 元に戻す
        3. yml のTZ=USにする
           1. 失敗
        4. 元に戻してみる
    3. install.sh に```pip3 install --upgrade --force-reinstall setuptools cython numpy```を追加18:52
        1. 失敗、効果なし
    4. install.sh に```pip install numpy==1.24.0```を追加18:57
        1. 失敗
    5. ```sudo apt install python3.10```をDockerfileに追加
        1. 実行不可のう
    6. ```pip3 install numpy==1.18.5```をinstall.shに19:14
        1. 変わらず
    7. install.shを```pip3 install -r ./requirements.txt```だけにする
        1. 失敗せる
    8. ```version: "3.12"```
        1. 失敗
    9. ```FROM python:3.9-slim```をDockerfileに
        1. 解決
19. ```Package 'openjdk-11-jre' has no installation candidate```が```[ltc stage-4 17/19] RUN cd /en-it && sh ./install.sh```で発生
    1. [ask ubuntu](https://askubuntu.com/questions/1203898/package-openjdk-11-jdk-has-no-installation-candidate)
       1. ```apt install openjdk-11-jdk\```を追加
          1. 実行不可
       2. ```apt-get install openjdk-11-jdk\```に変更
          1. 実行不可
       3. ```apt-get install -y default-jdk openjdk-11-jre```をinstall.shにおいて、requirementsより前に出す　19:52
          1. 成功
20. 完成
21. ```docker exec tmpltc bash```で始動できない
    1. どうやら.envがなかったことが問題?
22. ```docker-compose build --build-arg "LA1=en" --build-arg "LA2=it" && docker compose up -d```にたいし```no configuration file provided: not found```
    1. Lexicaltranslationcounterに写っていなかった
23. ```docker exec tmpltc bash```で中に入れない
    1. 中身が空?
    2. 一旦これをコピーし、まっさらな状態できちんと動くかを確認


