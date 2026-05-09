## Install awesome alignment
Access https://github.com/neulab/awesome-align and download [multilingually fine-tuned w/o --train_co, softmax model](https://drive.google.com/file/d/1IluQED1jb0rjITJtyj4lNMPmaRFyMslg/view?usp=sharing)

This pair is still on a more legacy runtime path than `de_en` or `en_ja`.

If you run locally from the repository root, set `ROOT=$(pwd)` and place the
extracted model under:

```text
$ROOT/src/model/awesome_model_without_co/
```

If `ROOT` is not set, the legacy default path is still:

```text
/root/src/model/awesome_model_without_co/
```
