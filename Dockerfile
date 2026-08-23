FROM python:3.12-slim

# uv, pinned to the version that produced uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/uv

WORKDIR /app

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Dependencies first, so this layer is rebuilt only when the lock file changes.
# --no-dev drops black and ruff; naming only the server group drops pygame,
# which the server has never imported and the old image installed anyway.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group server

# Copy game logic, server, web frontend, and wordlist
COPY game/ game/
COPY server/ server/
COPY web/ web/
COPY tools/ tools/
COPY data/ data/
COPY wordlist.py .

ENV PATH="/app/.venv/bin:$PATH"

# Pre-download and patch the Estonian Hunspell dictionary so first request is fast
RUN python -c "from wordlist import WordList; WordList()"

EXPOSE 8080

# Use $PORT env var if set (Heroku), otherwise default to 8080
CMD uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8080}
