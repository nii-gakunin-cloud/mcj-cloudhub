import os
from pathlib import Path

from jupyter_server import serverapp
from notebook import notebookapp
from IPython.core.display import HTML


def _get_running_servers():
    app_servers = list(notebookapp.list_running_servers())
    if len(app_servers) > 0:
        return app_servers
    return list(serverapp.list_running_servers())

def generate_edit_link(conf: Path) -> HTML:
    servers = _get_running_servers()
    if len(servers) > 0:
        nb_conf = servers[0]
        p = (
            Path(nb_conf["base_url"])
            / "edit"
            / conf.absolute().relative_to(nb_conf.get("notebook_dir") or nb_conf.get("root_dir"))
        )
    else:
        p = (
            Path(os.get_env["JUPYTER_SERVER_ROOT"])
            / "edit"
            / conf.absolute().relative_to(nb_conf["notebook_dir"])
        )

    return HTML(f'<a href={p} target="_blank">{p.name}</a>')