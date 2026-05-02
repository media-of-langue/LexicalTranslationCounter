#!/usr/bin/env python3
"""Set up a Docker-free local runtime for small LTC runs."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_AWESOME_MODEL_FILES = (
    "config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.txt",
)
NLTK_PACKAGES = (
    "omw-1.4",
    "averaged_perceptron_tagger",
    "punkt",
    "wordnet",
    "punkt_tab",
    "averaged_perceptron_tagger_eng",
)


@dataclass(frozen=True)
class RuntimeConfig:
    language_pair: str
    langs: tuple[str, str]
    requirements: tuple[str, ...]
    python_imports: tuple[str, ...]
    model_dir_name: str
    spacy_model: str | None = None
    extra_pip_packages: tuple[str, ...] = ()
    external_commands: tuple[str, ...] = ()

    @property
    def pair_underscore(self) -> str:
        return "_".join(self.langs)


RUNTIMES = {
    "de-en": RuntimeConfig(
        language_pair="de-en",
        langs=("de", "en"),
        requirements=(
            "shell_scripts/basis/requirements.txt",
            "shell_scripts/de/requirements.txt",
            "shell_scripts/en/requirements.txt",
            "shell_scripts/de-en/requirements.txt",
        ),
        python_imports=(
            "environ",
            "germalemma",
            "nltk",
            "pandas",
            "spacy",
            "torch",
            "transformers",
        ),
        model_dir_name="awesome_model_with_co",
        spacy_model="de_dep_news_trf",
        extra_pip_packages=("spacy<3.8.0",),
    ),
    "en-ja": RuntimeConfig(
        language_pair="en-ja",
        langs=("en", "ja"),
        requirements=(
            "shell_scripts/basis/requirements.txt",
            "shell_scripts/en/requirements.txt",
            "shell_scripts/ja/requirements.txt",
            "shell_scripts/en-ja/requirements.txt",
        ),
        python_imports=(
            "environ",
            "nltk",
            "pandas",
            "pyknp",
            "torch",
            "transformers",
        ),
        model_dir_name="awesome_model_without_co",
        external_commands=("jumanpp",),
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_pair(raw: str) -> str:
    return raw.strip().lower().replace("_", "-")


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def runtime_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["ROOT"] = str(root)
    return env


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def ensure_venv(venv_dir: Path, python_executable: str) -> Path:
    python_path = venv_python(venv_dir)
    if not python_path.exists():
        run([python_executable, "-m", "venv", str(venv_dir)], repo_root())
    return python_path


def install_deps(root: Path, python_path: Path, config: RuntimeConfig) -> None:
    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], root)
    for requirements in config.requirements:
        run([str(python_path), "-m", "pip", "install", "-r", requirements], root)
    for package in config.extra_pip_packages:
        run([str(python_path), "-m", "pip", "install", package], root)
    if config.spacy_model:
        run([str(python_path), "-m", "spacy", "download", config.spacy_model], root)


def install_nltk_data(root: Path, python_path: Path) -> None:
    nltk_dir = root / "nltk_data"
    nltk_dir.mkdir(exist_ok=True)
    run(
        [str(python_path), "-m", "nltk.downloader", "-d", str(nltk_dir), *NLTK_PACKAGES],
        root,
    )


def check_python_runtime(
    root: Path,
    python_path: Path,
    config: RuntimeConfig,
) -> None:
    lines = [
        "import importlib",
        f"for name in {config.python_imports!r}:",
        "    importlib.import_module(name)",
    ]
    if config.spacy_model:
        lines.extend(
            [
                "import spacy",
                f"spacy.load({config.spacy_model!r})",
            ]
        )
    print("+", str(python_path), "-c", f"<{config.language_pair} runtime check>")
    subprocess.run(
        [str(python_path), "-c", "\n".join(lines)],
        cwd=root,
        env=runtime_env(root),
        check=True,
    )


def missing_external_commands(root: Path, config: RuntimeConfig) -> list[str]:
    return [
        command
        for command in config.external_commands
        if shutil.which(command) is None
    ]


def check_awesome_align_model(root: Path, config: RuntimeConfig) -> list[Path]:
    model_dir = root / "src" / "model" / config.model_dir_name
    return [
        model_dir / file_name
        for file_name in REQUIRED_AWESOME_MODEL_FILES
        if not (model_dir / file_name).exists()
    ]


def print_external_command_help(root: Path, config: RuntimeConfig, missing: list[str]) -> None:
    print("\nMissing external runtime commands:")
    for command in missing:
        print(f"- {command}")
    print("\nFor en-ja, install Juman++ and make `jumanpp` available on PATH.")
    print("On macOS, Homebrew can install it with `brew install jumanpp`.")
    print("See:")
    print(f"  {root / 'documents' / config.language_pair / 'Readme.md'}")


def print_model_help(root: Path, config: RuntimeConfig, missing_files: list[Path]) -> None:
    rel_missing = [path.relative_to(root) for path in missing_files]
    print("\nMissing awesome-align model files:")
    for path in rel_missing:
        print(f"- {path}")
    print(f"\nDownload the {config.language_pair} awesome-align model manually and place it under:")
    print(f"  {root / 'src' / 'model' / config.model_dir_name}")
    print("See:")
    print(f"  {root / 'documents' / config.language_pair / 'Readme.md'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language-pair",
        default="de-en",
        choices=sorted(RUNTIMES),
        help="Local setup target.",
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
    args = parser.parse_args()
    args.config = RUNTIMES[normalize_pair(args.language_pair)]
    return args


def main() -> int:
    args = parse_args()
    config: RuntimeConfig = args.config
    root = repo_root()
    venv_dir = args.venv_dir.resolve()
    python_path = venv_python(venv_dir)

    if args.check_only:
        if not python_path.exists():
            print(f"missing virtual environment: {venv_dir}")
            return 1
        check_python_runtime(root, python_path, config)
    else:
        python_path = ensure_venv(venv_dir, args.python)
        install_deps(root, python_path, config)
        install_nltk_data(root, python_path)
        check_python_runtime(root, python_path, config)

    missing_commands = missing_external_commands(root, config)
    if missing_commands:
        print_external_command_help(root, config, missing_commands)
        return 2

    missing_files = check_awesome_align_model(root, config)
    if missing_files:
        print_model_help(root, config, missing_files)
        return 3

    la1, la2 = config.langs
    print(f"\nLocal {config.language_pair} runtime is ready.")
    print("Example:")
    print(
        f"  ROOT={root} {python_path} src/count_function.py 0 {la1} {la2} "
        f"--input-dir src/data/samples/{config.pair_underscore}/input --max-rows 1000"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
