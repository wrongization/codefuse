if not exist .venv (
    uv venv
)
uv lock
uv sync
pause