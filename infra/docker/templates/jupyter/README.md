# JupyterLab Notebook Template

Turnkey JupyterLab container for data exploration and ML prototyping.

## Quick Start

```bash
cd infra/docker/templates/jupyter
docker build -t jupyter-lab .
docker run -p 8888:8888 -v "$(pwd)":/workspace jupyter-lab
```

Open http://localhost:8888 (no token/password by default).

## Production Notes

- Set authentication: `-e JUPYTER_TOKEN=...` and add `--NotebookApp.token=${JUPYTER_TOKEN}` to CMD if you harden this image.
- Mount your notebooks/data: `-v /path/to/notebooks:/workspace`.
- GPU: extend FROM a CUDA base image and keep the same entrypoint.
- Add extra packages by editing `requirements.txt`.

## Ports & Health

- Port: `JUPYTER_PORT` (default 8888)
- Healthcheck: `http://localhost:${JUPYTER_PORT}/api/status`
