#!/usr/bin/env python3
"""Fetch and install a small LTC sample corpus package."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REPO = "media-of-langue/LexicalTranslationCounter"


@dataclass(frozen=True)
class SampleConfig:
    language_pair: str
    langs: tuple[str, str]
    tag: str
    asset: str
    package_name: str
    sha256: str

    @property
    def pair_underscore(self) -> str:
        return "_".join(self.langs)


SAMPLES = {
    "de-en": SampleConfig(
        language_pair="de-en",
        langs=("de", "en"),
        tag="ltc-sample-de-en-small-v1",
        asset="ltc-sample-de-en-small.tar.zst",
        package_name="ltc-sample-de-en-small",
        sha256="c7e5bfd6f71cfa72382ebb418d855712098076ad5a93ae156a450db7192ba277",
    ),
    "en-ja": SampleConfig(
        language_pair="en-ja",
        langs=("en", "ja"),
        tag="ltc-sample-en-ja-small-v1",
        asset="ltc-sample-en-ja-small.tar.zst",
        package_name="ltc-sample-en-ja-small",
        sha256="5eb4abdcd5881d6c860254958a36c65a0c0b6143985b888e8221e5f638717679",
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_pair(raw: str) -> str:
    return raw.strip().lower().replace("_", "-")


def default_sample_dir(config: SampleConfig) -> Path:
    return repo_root() / "src" / "data" / "samples" / config.pair_underscore


def build_url(repo: str, tag: str, asset: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{asset}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"download: {url}")
    with urllib.request.urlopen(url) as response:
        with out_path.open("wb") as out:
            shutil.copyfileobj(response, out)


def extract_archive(
    archive_path: Path,
    work_dir: Path,
    package_name: str | None,
) -> Path:
    subprocess.run(["tar", "-xf", str(archive_path), "-C", str(work_dir)], check=True)
    if package_name:
        package_dir = work_dir / package_name
        if package_dir.exists():
            return package_dir

    candidates = [
        path
        for path in work_dir.iterdir()
        if (path / "src" / "data" / "input").is_dir()
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"could not find package root with src/data/input under {work_dir}"
        )
    return candidates[0]


def install_package(package_dir: Path, sample_dir: Path, force: bool) -> None:
    source_input = package_dir / "src" / "data" / "input"
    if not source_input.is_dir():
        raise FileNotFoundError(f"input directory not found in package: {source_input}")

    if sample_dir.exists():
        if not force:
            raise FileExistsError(
                f"sample directory already exists: {sample_dir}. Use --force to replace it."
            )
        shutil.rmtree(sample_dir)

    sample_dir.mkdir(parents=True)
    shutil.copytree(source_input, sample_dir / "input")

    for name in ("README.md", "LICENSE-DATA.md", "MANIFEST.json"):
        src = package_dir / name
        if src.exists():
            shutil.copy2(src, sample_dir / name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language-pair",
        default="de-en",
        choices=sorted(SAMPLES),
        help="Sample language pair to fetch.",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--asset", default=None)
    parser.add_argument("--url", default=None, help="Direct asset URL override.")
    parser.add_argument(
        "--archive-path",
        type=Path,
        default=None,
        help="Use an existing local archive instead of downloading.",
    )
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=None,
        help="Install directory. Input files are written under <sample-dir>/input.",
    )
    parser.add_argument("--sha256", default=None)
    parser.add_argument("--package-name", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-sha256", action="store_true")
    args = parser.parse_args()

    config = SAMPLES[normalize_pair(args.language_pair)]
    args.config = config
    args.tag = args.tag or config.tag
    args.asset = args.asset or config.asset
    args.sha256 = args.sha256 or config.sha256
    args.package_name = args.package_name or config.package_name
    args.sample_dir = args.sample_dir or default_sample_dir(config)
    return args


def main() -> None:
    args = parse_args()
    config: SampleConfig = args.config
    url = args.url or build_url(args.repo, args.tag, args.asset)
    sample_dir = args.sample_dir.resolve()

    with tempfile.TemporaryDirectory(prefix="ltc-sample-") as tmp:
        work_dir = Path(tmp)
        archive_path = (
            args.archive_path.resolve() if args.archive_path else work_dir / args.asset
        )
        if args.archive_path is None:
            download(url, archive_path)

        if not args.skip_sha256:
            actual = file_sha256(archive_path)
            if actual != args.sha256:
                raise ValueError(
                    f"sha256 mismatch for {archive_path}: expected {args.sha256}, got {actual}"
                )

        package_dir = extract_archive(archive_path, work_dir, args.package_name)
        install_package(package_dir, sample_dir, force=args.force)

    input_dir = sample_dir / "input"
    la1, la2 = config.langs
    print(f"installed: {sample_dir}")
    print(f"input_dir: {input_dir}")
    print("try:")
    print(f"  python3 scripts/setup_local_runtime.py --language-pair {config.language_pair}")
    print(
        f"  ROOT=$(pwd) .venv/bin/python src/count_function.py 0 {la1} {la2} "
        f"--input-dir {input_dir} "
        f"--output-dir src/data/output/{config.pair_underscore}_sample "
        "--max-rows 1000"
    )


if __name__ == "__main__":
    main()
