# アーキテクチャおよびリファクタリング計画

[English version](Architecture_and_Refactor_Plan.md)

## 目的

この文書は、Lexical Translation Counter の目指すべきリポジトリ構造と
システム設計を記述するものです。

目的は、現在のリポジトリを捨てて作り直すことではありません。
現在の有用な核を活かしながら、コードベースをより理解しやすく、
拡張しやすく、テストしやすく、貢献しやすいものへ変えていくことです。

現在の概念的な分割自体は良いものです。

- alignment
- normalization
- morphological analysis

リファクタリングではこの分割を維持しつつ、その境界と責務の置き方を見直します。

## 現在の構造における主な問題

- counting スクリプトに、CLI 処理、コーパス IO、再開処理、wordlist 更新、
  alignment 実行、集計、出力書き込みが混在している
- 言語ごと・言語ペアごとの実装が Python モジュール名に埋め込まれており、
  拡張しづらい
- alignment 実装に大きな重複がある
- テストは手作業での確認には有用だが、コントリビュータ向けの自動テストとしては
  まだ整理されていない
- wordlist 管理と relation 集計が結合しており、再現性やレビュー性を下げている
- 入出力形式が強く型付けされておらず、中央で定義されてもいない

## リファクタリングの目標

- ディレクトリ構造だけ見ても全体像が理解しやすいこと
- counting pipeline が明示的でモジュール化されていること
- 新言語追加が、できるだけコード複製ではなく設定追加で済むこと
- 複数の alignment backend を自然に扱えること
- 軽量な参加者向けテストと、重いモデル依存テストを分離すること
- 移行中は、可能な限り現在の挙動を維持すること

## 設計原則

- ドメイン概念を明示的に保つ
- 命名規約よりも設定を優先する
- 差し替え可能な backend には共有 interface を使う
- 純粋なデータ変換と副作用のある IO を分ける
- 初参加者の導線は小さくローカルに保つ
- counting、lexicon building、evaluation を別 workflow として扱う

## 重要な修正: 移行用の形とクリーンスタート時の理想形は同じではない

現在の `src/ltc/` パッケージ構造は、移行用の足場としては良いものです。
ただし、もしこのプロジェクトを今ゼロから設計するなら、
それがそのまま理想的な最終構造になるわけではありません。

もし最初から作るなら、リポジトリは次の軸で構成されるべきです。

- 安定したドメイン成果物
- 明示的な workflow の段階
- 差し替え可能な言語 backend と alignment backend
- コントリビュータが編集しやすい設定
- そのまま実行できる contributor 向け project template

より重要なのは、このタスクの中心を次のようには捉えないことです。

- 「既存 wordlist を使って corpus から count する」

その代わり、次のように捉えるべきです。

- 「parallel corpus から、sentence と結びついた bilingual translation observation
  を抽出し、それを relation table や任意の lexicon table に集計する」

これが最大の設計上の修正点です。

## クリーンスタート時のドメインモデル

もしこのプロジェクトをゼロから設計するなら、主要な第一級概念は
次のようになるべきです。

- `CorpusRow`
- `SentenceAnalysis`
- `AlignmentEdge`
- `TranslationObservation`
- `RelationAggregate`
- `LexiconEntry`

特に、legacy 設計に欠けている中核概念が `TranslationObservation` です。

`TranslationObservation` は、
「正規化済みの source expression と target expression が、
ある sentence pair の中で対応づけられた」という1件の証拠です。

そこには例えば次の情報を持たせるべきです。

- corpus row id
- source / target の token span
- source / target の正規化形
- source / target の品詞
- aligner / backend 名
- 利用できる場合は confidence や score

この概念が入ると、relation table は一次成果物ではなく、
observation に対する集約結果になります。

## クリーンスタート時の目標ディレクトリ構造

もしこのプロジェクトを、OSS 貢献と多言語拡張を前提にゼロから設計するなら、
より自然な構造は次のようになります。

```text
.
|-- README.md
|-- pyproject.toml
|-- configs/
|   |-- languages/
|   |-- pairs/
|   `-- workflows/
|-- projects/
|   |-- minimal/
|   |-- smoke/
|   `-- pair_templates/
|-- src/
|   `-- ltc/
|       |-- __init__.py
|       |-- cli/
|       |   |-- analyze.py
|       |   |-- align.py
|       |   |-- extract.py
|       |   |-- aggregate.py
|       |   |-- inspect.py
|       |   |-- evaluate.py
|       |   `-- wordlists.py
|       |-- domain/
|       |   |-- corpus.py
|       |   |-- analysis.py
|       |   |-- alignments.py
|       |   |-- observations.py
|       |   |-- lexicon.py
|       |   `-- relations.py
|       |-- artifacts/
|       |   |-- schemas.py
|       |   |-- readers.py
|       |   `-- writers.py
|       |-- workflows/
|       |   |-- analyze.py
|       |   |-- align.py
|       |   |-- extract_observations.py
|       |   |-- aggregate_relations.py
|       |   `-- checkpoints.py
|       |-- backends/
|       |   |-- alignment/
|       |   |   |-- base.py
|       |   |   |-- awesome_align.py
|       |   |   |-- binary_align.py
|       |   |   `-- fast_align.py
|       |   `-- linguistic/
|       |       |-- base.py
|       |       |-- stanza.py
|       |       |-- spacy.py
|       |       `-- jumanpp.py
|       |-- rules/
|       |   |-- languages/
|       |   `-- pairs/
|       |-- registry/
|       |   |-- languages.py
|       |   `-- language_pairs.py
|       `-- evaluation/
|           |-- smoke.py
|           `-- metrics.py
|-- tests/
|   |-- unit/
|   |-- smoke/
|   |-- integration/
|   `-- fixtures/
`-- documents/
```

これは最終的に目指すべき end-state の方向性です。

現在導入した `src/ltc/` パッケージは、この形へ向かうための
移行用の足場として理解するべきであり、
それ自体を完璧な最終構造とみなすべきではありません。

## 移行用構造と最終構造の違い

移行中は、より単純な中間構造を持つことは妥当です。

- `src/ltc/io/`
- `src/ltc/pipeline/`
- `src/ltc/config/`

これらは現実的な踏み石です。

ただし最終的には、次の方向へ寄せるべきです。

- `domain`: データが何を意味するか
- `artifacts`: どの形式で保存・受け渡しするか
- `workflows`: パイプラインの段階をどう組み立てるか
- `rules`: 言語固有・言語ペア固有のヒューリスティクス
- repo 直下の `configs/`: コントリビュータが編集しやすい支援設定
- repo 直下の `projects/`: そのまま動かせる contributor 向け entry point

## ディレクトリごとの責務

### `src/ltc/domain/`

プロジェクト全体で使う正準なデータ構造を定義します。

例:

- `CorpusRow`
- `SentenceAnalysis`
- `AlignmentEdge`
- `TranslationObservation`
- `RelationAggregate`
- `LexiconEntry`

この層は、できるだけ project-specific な振る舞いを持たないべきです。

### `src/ltc/artifacts/`

データの読み書きを担当します。

例:

- corpus shard の読み書き
- observation dataset の読み書き
- relation table の export
- lexicon table の export
- checkpoint の読み書き

この層は、ファイル形式や schema version は知っていてよいですが、
言語的判断を持つべきではありません。

### `src/ltc/workflows/`

end-to-end workflow を担当します。

例:

- corpus row の analysis
- aligner の実行
- translation observation の抽出
- relation の集計
- checkpoint からの再開

この層は orchestration を担当し、backend 固有の実装を持つべきではありません。

### `src/ltc/backends/`

差し替え可能な実装を担当します。

これには例えば次が含まれます。

- alignment backend
- tokenization / POS backend
- lemmatization / normalization helper

pipeline は concrete module ではなく backend interface に依存するべきです。

### `configs/`

言語ごと・言語ペアごとの設定を担当します。

例:

- `ja` の既定 linguistic backend
- `en-ja` の既定 aligner
- 品詞フィルタ方針
- backend 固有の option

ここが、「新言語追加 = Python ファイルをコピーして修正する」から、
「まず設定を追加し、必要なときだけコードを書く」へ変えるための鍵です。

この設定を Python package の外に置くことで、
内部実装に詳しくないコントリビュータでもレビュー・編集しやすくなります。

### `src/ltc/registry/`

利用可能な言語、言語ペア、backend 選択肢への検証付きアクセスを提供します。

例えば次の問いに答える層です。

- この言語はサポートされているか
- この言語ペアの既定 backend は何か
- どの設定ファイルを読むべきか

### `src/ltc/rules/`

単純な宣言的設定だけでは表せない、言語固有・言語ペア固有のロジックを担当します。

例:

- multiword merge rule
- auxiliary / copula のフィルタ
- script 固有の normalization exception
- post-alignment cleanup

### `projects/`

コントリビュータがそのまま実行できる template 群を担当します。

例:

- minimal な end-to-end sample run
- 1つの言語ペア用の smoke-test project
- 新規サポート追加時に必要なファイルを示す pair template

この考え方は、再利用可能な package code と、再現可能な workflow 定義・asset・
依存・出力を分けている spaCy Projects の設計に強く学んだものです。

## 推奨される pipeline 形状

主要 workflow は、次の明示的な段階に分かれるべきです。

1. corpus row を読む
2. 両文を token, POS, lemma, normalized form へ分析する
3. analyzed sentence に対して aligner backend を走らせる
4. 生の alignment 出力を canonical な `AlignmentEdge` に変換する
5. 言語ルール・言語ペアルールを適用する
6. `TranslationObservation` を出力する
7. observation を relation table に集約する
8. 必要であれば lexicon table を派生または更新する
9. 出力と checkpoint を保存する

この形にすると、各段階の入出力が明確になり、デバッグしやすくなります。

また、最終 CSV だけでなく中間成果物も確認できるようになるため、
コントリビュータが動作を追いやすくなります。

OSS の使いやすさという観点では、
参加者が最初から全体構造を理解しなくても、
1つの名前付き small project をすぐ動かせることが重要です。

## Backend Interface

プロジェクトは、少数の安定した interface を採用するべきです。

例:

```python
class LinguisticBackend(Protocol):
    def analyze(self, sentence: str, language: str) -> AnalyzedSentence: ...


class AlignmentBackend(Protocol):
    def align(
        self,
        source: AnalyzedSentence,
        target: AnalyzedSentence,
        pair_config: LanguagePairConfig,
    ) -> list[AlignmentEdge]: ...
```

重要なのは次の点です。

- pipeline は、それが Awesome Align なのか、BinaryAlign なのか、
  FastAlign なのかを知らなくてよい
- pipeline は canonical output type だけを知っていればよい

同じ原則は linguistic analysis にも当てはまります。

workflow は、その分析が次のどれから来たかを知らなくてよいです。

- Juman++
- Stanza
- spaCy
- その他の言語固有実装

workflow は canonical な analyzed sentence shape のみを知るべきです。

## 言語・言語ペア設定

ある言語が既存 backend で処理できるなら、
新規言語追加は理想的には設定だけで済むべきです。

例 `configs/languages/ja.yaml`:

```yaml
code: ja
linguistic_backend: jumanpp
content_pos:
  - NOUN
  - VERB
  - ADJ
  - ADV
normalization:
  use_lemma: true
  exception_table: normalize_data/ja/
```

例 `configs/pairs/en-ja.yaml`:

```yaml
pair: en-ja
alignment_backend: awesome_align
source_language: en
target_language: ja
postprocess:
  ignore_copula_support: true
  merge_multiword_content_tokens: true
```

これは、大きな Python モジュールをコピーしてレビューするよりも、
はるかに扱いやすい形です。

## Lexicon / Wordlist 設計

もしゼロから設計するなら、lexicon table は
主 pipeline の前提入力ではなく、派生成果物または curated overlay であるべきです。

つまり canonical flow は次のようになるべきです。

- corpus
- analysis
- alignments
- translation observations
- relation aggregation
- optional lexicon export

そして次のような流れではない方がよいです。

- corpus
- pre-existing wordlists
- counting

これは legacy 設計から見るとかなり大きな変更です。

これが良い理由は次のとおりです。

- 新言語 onboarding が軽くなる
- コントリビュータが試す前に巨大 wordlist を準備しなくてよい
- observation 抽出が、corpus と backend 選択から再現可能になる
- lexicon curatation を別 workflow としてレビューしやすくなる

実際の移行では legacy wordlist support を互換性のために残してもよいですが、
それは compatibility layer として扱うべきであり、
理想構造の中心に置くべきではありません。

## Relation Counting と Wordlist Building は分離するべき

現在のリポジトリでは、欠けている normalized word を
counting 中に追加していく発想があります。

これは次の2 workflow に分けるべきです。

- wordlist update の構築または提案
- 承認済み wordlist に対する relation counting

この分離により、次の点が改善されます。

- 再現性
- レビュー性
- デバッグ容易性
- コントリビュータの安心感

## 推奨される artifact 戦略

中間成果物も第一級 output として保存するべきです。

推奨 artifact:

- analyzed corpus rows
- alignment edges
- translation observations
- aggregated relation tables
- optional lexicon tables

最終 public output や downstream output は、互換性のために CSV を含んでもよいです。
ただし中間成果物は、より構造化された形式を使うべきです。

- JSONL: 人が見やすく検査しやすい
- Parquet: 規模が大きいときに有利

正確なファイル形式そのものよりも、
安定した schema と明示的な versioning を持つことの方が重要です。

この考え方は、処理済みデータを一時的な script output ではなく、
保存・再読み込み可能な artifact として扱う Hugging Face Datasets の流儀にも近いです。

## テスト構造

テストは `src/test/` から外し、標準的な `tests/` ツリーへ移すべきです。

推奨分割:

- `tests/unit/`
- `tests/smoke/`
- `tests/integration/`
- `tests/fixtures/`

### `tests/unit/`

純粋関数ベースのテストです。

例:

- normalization helper
- aggregation logic
- checkpoint behavior
- schema conversion

モデル download なし、重い依存なしで動くべきです。

### `tests/smoke/`

参加者向けの小さなテストです。

fresh clone 直後でも高速に回り、次を保証するべきです。

- package import ができる
- 小さな pair config が動く
- tiny corpus が pipeline を通る
- observation extraction が end-to-end で動く

### `tests/integration/`

実際の backend install や model asset が必要なテストです。

これらは opt-in、もしくは別 mark で分離するべきです。

## 移行戦略

リファクタリングは段階的に進めるべきです。

### Phase 1: 新しい境界の導入

- 新しい package layout を追加する
- schema と interface を定義する
- 既存コードを adapter 経由で包む
- まだ挙動は変えない

### Phase 2: 共有ロジックの移動

- alignment post-processing の共通部分を抽出する
- IO と checkpoint の共通部分を抽出する
- 現在の counting script を workflow module に移す

### Phase 3: 参照実装となる1言語ペアの移植

- 1つの言語ペアを最初の fully migrated path に選ぶ
- 新旧 output を比較する
- 新 interface を安定化する
- `TranslationObservation` を明示的 artifact として導入する

現段階では、`en_ja` をその参照実装として扱うべきです。
主要言語へ広げる前に、まず `en_ja` の alignment quality を改善します。
その改善過程で、backend logic、heuristics、observation、evaluation の
切り分けを見直した方がよいと分かる可能性があるため、その学びが構造に
反映されるまでは Phase 4 を急がない方がよいです。

### Phase 4: 残り言語ペアの移植

- 言語ペアごとに移行する
- 各 migrated path の検証が終わるまで legacy module を残す

### Phase 5: Legacy 構造の撤去

- legacy module への直接 import を非推奨化する
- contributor docs を新しい flow に合わせて書き直す

## 実務上の修正後方針

現在の package refactor は依然として有用であり、そのまま活かしてよいです。

ただし長期的な設計方向は、次のように理解し直すべきです。

- artifact-driven workflow へ寄せる
- observation を第一級概念にする
- lexicon generation は前提ではなく downstream に寄せる
- backend choice は pluggable に保つ
- 言語・言語ペア対応はできるだけ config-driven にする

この方向の方が、もし今このシステムを
「多言語対応の OSS プロジェクト」としてゼロから始めるなら、
より自然な設計に近いです。
