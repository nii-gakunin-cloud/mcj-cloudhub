"""
Scan repository for README.md files and copy them into one directory preserving
relative structure, converting each README.md into an {title}.md

Usage:
    python tools/generate_docs_from_readmes.py [--root PATH] [--out DIR] [--config FILE] [--exist_ok] [--static_docs_dir DIR] [--update_config]

Defaults:
    root = repository root (script location's parent)
    out = docs
    config = zensical.toml
    exist_ok = False (error if output file already exists)
    static_docs_dir = docs (optional directory containing additional static markdown files to include in the docs)
    update_config = False (whether to update the zensical config file with the generated nav)

The script excludes certain directories (e.g. .git, node_modules, .venv, docs)
by default. Adjust `EXCLUDE_DIRS` as needed.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil

import tomli_w


EXCLUDE_DIRS = {".git", "docs", "node_modules", ".venv", "venv",
                "images", "notebooks", "build", "dist", "mcj-data"}
BASE_CONFIG = {'project': {'site_name': 'MCJ-CloudHub',
                           'docs_dir': 'docmerged',
                           'language': 'ja',
                           'repo_url': 'https//github.com/nii-gakunin-cloud/mcj-cloudhub',
                           'theme': {'features': ["navigation.top",
                                                  "navigation.path"]
                                     }
                           }
               }


def get_title_from_md(md: Path) -> str:
    """
    Get the title for the doc page from the first line of the README.md.
    If the first line starts with a markdown header (e.g. "# Title"), use that as the title.
    Otherwise, use the filename as the title.
    """
    with open(md) as f:
        content = f.readline()
        if content.startswith("#"):
            return content.strip().lstrip("#").strip()
    return md.stem


def merge_static_docs(out: Path, nav: dict, static_docs_dir: Path = None) -> None:
    """
    If there are static docs in {static_docs_dir}, copy them into the output directory.
    This allows you to include additional markdown files that are not generated from README.md.
    """
    if not static_docs_dir.exists():
        print(f"Static docs directory {static_docs_dir} does not exist, skipping")
        return
    if not static_docs_dir.is_dir():
        return
    for md in static_docs_dir.rglob("*.md"):
        rel = md.relative_to(static_docs_dir)
        target_file = out.joinpath(rel)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md, target_file)
        nav.append({get_title_from_md(md): str(rel)})
    images_dir = static_docs_dir.joinpath("images")
    if images_dir.exists() and images_dir.is_dir():
        target_images_dir = out.joinpath("images")
        shutil.copytree(images_dir, target_images_dir, dirs_exist_ok=True)
    print(f"Copied static docs from {static_docs_dir} into {out}")


def collect_readmes(root: Path, out: Path, nav: dict, exist_ok: bool) -> dict:

    def _should_exclude(path: Path) -> bool:
        for part in path.parts:
            if part in EXCLUDE_DIRS:
                return True
        return False

    copied = 0
    for md in root.rglob("README.md"):
        print(f"Found README: {md}")
        rel = md.relative_to(root)
        if _should_exclude(rel):
            continue
        fname = get_title_from_md(md)
        target_file = out.joinpath(f"{fname}.md")
        if target_file.exists():
            if not exist_ok:
                raise SystemExit(f"Error: {target_file} already exists")
            print(f"Warning: {target_file} already exists, skipping {md}")
            continue
        shutil.copy2(md, target_file)
        images_dir = md.parent.joinpath("images")
        if images_dir.exists() and images_dir.is_dir():
            # FIXME: Not copy exist image again
            target_images_dir = out.joinpath("images")
            shutil.copytree(images_dir, target_images_dir, dirs_exist_ok=True)
        nav.append({fname: f"{fname}.md"})
        copied += 1
    print(f"Copied {copied} README files into {out}")

    # Root README.md is required to be index page, so the file name must be README.md or index.md
    # So update here
    # Ref: https://www.mkdocs.org/user-guide/writing-your-docs/#index-pages
    shutil.copy2(os.path.join(root, 'README.md'), out.joinpath('README.md'))

    return nav


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="repository root to scan")
    p.add_argument("--out", default="docmerged", help="output docs directory")
    p.add_argument("--config", default="zensical.toml", help="mkdocks config file")
    p.add_argument("--exist_ok", default=False, action="store_true", help="error if output file exists")
    p.add_argument("--static_docs_dir", nargs="?", default="docs", help="optional directory containing additional static markdown files to include in the docs")
    p.add_argument("--update_config", default=False, action="store_true", help="whether to update the zensical config file with the generated nav (default: False)")
    args = p.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    config = Path(args.config).resolve()
    exist_ok = args.exist_ok
    static_docs_dir = Path(args.static_docs_dir).resolve() if args.static_docs_dir else None
    update_config = args.update_config

    if not root.exists():
        raise SystemExit(f"root not found: {root}")

    if update_config is True:
        data = BASE_CONFIG

    # clear and recreate out dir
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    nav = list()  # reset nav
    collect_readmes(root, out, nav, exist_ok)

    merge_static_docs(out, nav, root.joinpath(static_docs_dir))
    # write nav to zensical config file
    if update_config is True:
        data["project"]["nav"] = nav
        with open(config, 'wb') as f:
            tomli_w.dump(data, f)


if __name__ == "__main__":
    main()
