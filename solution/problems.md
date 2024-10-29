問題
-
# dockerにwordlistが入っていない
## プロセス
1. 手元のデータをdockerhubにアップロード
2. inamiパソコンに入る
3. inami PCからdockerを構築
4. docker構築時にコピー
5. docker完成

## 原因リスト
* ~~手元のデータの欠損~~
* ~~dockerアップロード時の欠損~~
* ~~コピー時の欠損~~
* docker完成時

## 特定
## dockerアップロード時の欠損
### 方針
* 本当にdockerに上がっているかを引っ張ってきて作る
### 手法
1. ```docker run -it --rm aaakmn/wordlist_it```で中のものを明示的にして、中のものを確認
2. ``` cd src/data/input/```
3. ```cat wordlist_it_verb.csv```をする

4. 存在していた

<details>

```
10403,presse
10404,appezzano
10405,resistito
10406,regalerà
10407,affilate
10408,pianificano
```
</details>

### 結論
* dockerにはきちんと挙げられている

## コピー時の問題
### 方針
* 手元で同様のコピーを作成するだけのコードを書く
### 手法
1. dockerのコードを書く
``` docker
FROM aaakmn/wordlist_it:latest AS wordlist
COPY --from=wordlist /src/data/input/wordlist* /root/src/data/input/
CMD [ "/bin/bash" ]
```
2. dockerを構築
```docker
FROM aaakmn/wordlist_it:latest AS wl
FROM ubuntu:latest
COPY --from=wl /src/data/input/wordlist* /root/src/data/input/

CMD [ "/bin/bash" ]
```
3. 中身を確認  ```head -n 10 wordlist_it_noun.csv```
4. 存在していた
<details>
```
0,Ricevi
1,risposte
2,personale
3,struttura
4,Grill
5,Seafood
6,Bar
7,visitatori
8,Istruzione
```
</details>

## docker完成時の問題
### 方針
* 段階を踏まえてdockerを作成してどこで崩壊しているか確認
### 手法1
1. wordlist_enも入れる
<details>
```docker 
ARG LA1=en
ARG LA2=it
FROM mediaoflangue/wordlist_${LA1}:latest AS wordlist1
FROM aaakmn/wordlist_${LA2}:latest AS wordlist2
FROM aaakmn/corpus_${LA1}_${LA2}:latest AS corpus
FROM nvidia/cuda:11.6.2-base-ubuntu20.04
COPY --from=wordlist1 /src/data/input/wordlist* /root/src/data/input/
COPY --from=wordlist2 /src/data/input/wordlist* /root/src/data/input/
COPY --from=corpus /src/data/input/corpus* /root/src/data/input/
```
</details>

2. ```cd root/src/data/input/```
3. ```head -n 10 wordlist_it_noun.csv```
4. 全部あった

### 手法2
1. docker-composeを使用(使用しているのと同じもの、名前のみ変更)
2. 不可、全て消えた
3. volumes消去
4. 全部あった

### dockerfileを元に戻す
1. install関連のみ消した状態
2. 全て存
3. 全部元の環境
4. spacyがinstallできない
5. requirementsに
```numpy==2.1.2 ```を書く

1. basisのinstallができない
2. 
3. ディスクの空き容量を確認
```
# 不要な Docker イメージを削除
docker image prune -a

# 不要なコンテナを削除
docker container prune
```
5. requirementsに
```numpy ```を書く
6. dockerfileにpython:3.12を追加


