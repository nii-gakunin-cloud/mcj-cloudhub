import glob
import json
import os


def _remove_recursive(d, keys: list):

    if isinstance(d, dict):
        for k, v in d.items():

            if k in keys:
                del d[k]
                return

            if isinstance(v, dict) or isinstance(v, list):
                _remove_recursive(v, keys)

    elif isinstance(d, list):
        for i, v in enumerate(d):

            if v in keys:
                del d[i]
                return

            if isinstance(v, dict) or isinstance(v, list):
                _remove_recursive(v, keys)

                
def remove_metadata(notebook_path, keys: list):

    print('target:', glob.glob(notebook_path))
    for p in glob.glob(notebook_path):
        with open(p, 'r') as f:
            notebook = json.load(f)

        _remove_recursive(notebook, keys)

        with open(p, 'w') as f:
            json.dump(notebook, f, indent=1, ensure_ascii=False)

        with open(p, 'a') as f:
            f.write('\n')


remove_metadata(f'{os.path.dirname(__file__)}/*.ipynb',
                ['lc_wrapper', "lc_cell_meme", "lc_notebook_meme"])
