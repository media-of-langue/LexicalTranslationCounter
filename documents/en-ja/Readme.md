## Install awesome alignment
Access https://github.com/neulab/awesome-align and download [multilingually fine-tuned w/o --train_co, softmax model](https://drive.google.com/file/d/1IluQED1jb0rjITJtyj4lNMPmaRFyMslg/view?usp=sharing)

Create `src/model/awesome_model_without_co/` in this repository and save the
extracted contents there. In the Docker runtime, the same files must be
available at `/root/src/model/awesome_model_without_co/`.

## Install Juman++

The en-ja runtime uses `pyknp`, which calls Juman++. Install Juman++ and make
the `jumanpp` command available on `PATH`.

On macOS with Homebrew:

```
brew install jumanpp
```
