import argparse
import json
from pathlib import Path


DEFAULT_TARGETS = ['lc_wrapper', 'lc_cell_meme', 'lc_notebook_meme']


def _remove_recursive(d, targets: list):

    if isinstance(d, dict):
        ks = set(d.keys())
        for key in ks:
            v = d[key]
            if key in targets:
                del d[key]
                continue

            _remove_recursive(v, targets)

    elif isinstance(d, list):
        i = 0
        for _ in range(len(d)):

            v = d[i]
            if isinstance(v, str) and v in targets:
                del d[i]
                continue

            _remove_recursive(v, targets)

            i += 1


def collect_notebook_paths(paths: list[str]) -> list[Path]:

    collected_paths = []
    seen_paths = set()

    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f'Path does not exist: {path}')

        if path.is_file():
            if path.suffix != '.ipynb':
                raise ValueError(f'Not a notebook file: {path}')
            notebook_paths = [path]
        elif path.is_dir():
            notebook_paths = sorted(path.rglob('*.ipynb'))
        else:
            raise ValueError(f'Unsupported path type: {path}')

        for notebook_path in notebook_paths:
            if notebook_path not in seen_paths:
                seen_paths.add(notebook_path)
                collected_paths.append(notebook_path)

    return collected_paths


def remove_metadata(notebook_paths: list[Path], targets: list):

    print('target:', [str(path) for path in notebook_paths])
    for path in notebook_paths:
        with open(path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        _remove_recursive(notebook, targets)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1, ensure_ascii=False)

        with open(path, 'a', encoding='utf-8') as f:
            f.write('\n')


def main():

    parser = argparse.ArgumentParser(
        description='Remove LC metadata from notebook files.'
    )
    parser.add_argument(
        'paths',
        nargs='*',
        default=[str(Path(__file__).resolve().parent)],
        help='Notebook file or directory. Directories are searched recursively for *.ipynb.',
    )
    args = parser.parse_args()

    notebook_paths = collect_notebook_paths(args.paths)
    remove_metadata(notebook_paths, DEFAULT_TARGETS)


if __name__ == "__main__":
    main()
