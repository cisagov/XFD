FROM python:3.12-slim

WORKDIR /opt/connector

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY tests/ tests/

# Relative imports in src/main.py require running as a module, not a script -- see README.md.
ENTRYPOINT ["python3", "-m", "src.main"]
