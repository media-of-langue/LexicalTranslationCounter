#!/usr/bin/env python3
"""Set up a Docker-free local runtime for small LTC runs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SUPPORTED_PAIR = "de-en"
REQUIRED_AWESOME_MODEL_FILES = (
    "config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.txt",
)
NLP_REQUIREMENTS = (
    "shell_scripts/basis/requirements.txt",
    "shell_scripts/de/requirements.txt",
    "shell_scripts/en/requirements.txt",
    "shell_scripts/de-en/requirements.txt",
)
NLTK_PACKAGES = (
    "omw-1.4",
    "averaged_perceptron_tagger",
    "punkt",
    "wordnet",
    "punkt_tab",
    "averaged_perceptron_tagger_eng",
)
PYTHON_IMPORTS = (
    "environ",
    "germalemma",
    "nltk",
    "pandas",
    "spacy",
    "torch",
    "transformers",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def ensure_venv(venv_dir: Path, python_executable: str) -> Path:
    python_path = venv_python(venv_dir)
    if not python_path.exists():
        run([python_executable, "-m", "venv", str(venv_dir)], repo_root())
    return python_path


def install_deps(root: Path, python_path: Path) -> None:
    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], root)
    for requirements in NLP_REQUIREMENTS:
        run([str(python_path), "-m", "pip", "install", "-r", requirements], root)

    # shell_scripts/de/install.sh also installs spaCy and the German model.
    run([str(python_path), "-m", "pip", "install", "spacy<3.8.0"], root)
    run([str(python_path), "-m", "spacy", "download", "de_dep_news_trf"], root)


def install_nltk_data(root: Path, python_path: Path) -> None:
    nltk_dir = root / "nltk_data"
    nltk_dir.mkdir(exist_ok=True)
    run(
        [str(python_path), "-m", "nltk.downloader", "-d", str(nltk_dir), *NLTK_PACKAGES],
        root,
    )


def check_python_runtime(root: Path, python_path: Path) -> None:
    code = "\n".join(
        [
            "import importlib",
            "import spacy",
            f"for name in {PYTHON_IMPORTS!r}:",
            "    importlib.import_module(name)",
            "spacy.load('de_dep_news_trf')",
        ]
    )
    env = os.environ.copy()
    env["ROOT"] = str(root)
    print("+", str(python_path), "-c", "<de-en runtime check>")
    subprocess.run([str(python_path), "-c", code], cwd=root, env=env, check=True)


def check_awesome_align_model(root: Path) -> list[Path]:
    model_dir = root / "src" / "model" / "awesome_model_with_co"
    return [
        model_dir / file_name
        for file_name in REQUIRED_AWESOME_MODEL_FILES
        if not (model_dir / file_name).exists()
    ]


def print_model_help(root: Path, missing_files: list[Path]) -> None:
    rel_missing = [path.relative_to(root) for path in missing_files]
    print("\nMissing awesome-align model files:")
    for path in rel_missing:
        print(f"- {path}")
    print("\nDownload the de-en awesome-align model manually and place it under:")
    print(f"  {root / 'src' / 'model' / 'awesome_model_with_co'}")
    print("See:")
    print(f"  {root / 'documents' / 'de-en' / 'Readme.md'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language-pair",
        default=SUPPORTED_PAIR,
        choices=[SUPPORTED_PAIR],
        help="Local setup target. Only de-en is supported for now.",
    )
    parser.add_argument(
        "--venv-dir",
        type=Path,
        default=repo_root() / ".venv",
        help="Virtual environment directory.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create the virtual environment.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check the virtual environment and awesome-align model files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    venv_dir = args.venv_dir.resolve()
    python_path = venv_python(venv_dir)

    if args.check_only:
        if not python_path.exists():
            print(f"missing virtual environment: {venv_dir}")
            return 1
        check_python_runtime(root, python_path)
    else:
        python_path = ensure_venv(venv_dir, args.python)
        install_deps(root, python_path)
        install_nltk_data(root, python_path)
        check_python_runtime(root, python_path)

    missing_files = check_awesome_align_model(root)
    if missing_files:
        print_model_help(root, missing_files)
        return 2

    print("\nLocal de-en runtime is ready.")
    print("Example:")
    print(
        f"  ROOT={root} {python_path} src/count_function.py 0 de en "
        "--input-dir src/data/samples/de_en/input --max-rows 1000"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
