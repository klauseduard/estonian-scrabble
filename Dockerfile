FROM python:3.12-slim

WORKDIR /app

# Install only server dependencies (no Pygame needed)
COPY requirements.txt requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy game logic, server, web frontend, and wordlist
COPY game/ game/
COPY server/ server/
COPY web/ web/
COPY wordlist.py .

# Pre-download Estonian Hunspell dictionary files so first request is fast
RUN python -c "from wordlist import WordList; WordList()"

EXPOSE 8080

# Use $PORT env var if set (Heroku), otherwise default to 8080
CMD uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8080}
