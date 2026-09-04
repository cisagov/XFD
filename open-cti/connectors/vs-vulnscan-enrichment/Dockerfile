FROM python:3.12-slim

WORKDIR /opt/connector

# Zscaler TLS-inspects outbound HTTPS on this network -- identical setup to connectors A/D's
# Dockerfiles (see their comments/README.md "TLS interception" for the full explanation). Reused
# verbatim rather than rediscovered: this is a property of the *network*, not of any one
# connector -- every connector's build hits the same failure.
#
# Pulled from a named build context (docker-compose.yml's additional_contexts, pointed at
# /opt/open-cti/tls -- runtime state, never this repo checkout), never COPYed from anywhere
# inside this directory -- the cert never touches git.
COPY --from=zscaler_cert zscaler.pem /usr/local/share/ca-certificates/zscaler.crt
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY tests/ tests/

# Relative imports in src/main.py require running as a module, not a script -- see README.md.
ENTRYPOINT ["python3", "-m", "src.main"]
