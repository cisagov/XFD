FROM python:3.12-slim

WORKDIR /opt/connector

# Zscaler TLS-inspects outbound HTTPS on this network, re-signing it with its own root CA -- the
# EC2 host trusts it, a fresh build container doesn't, hence pip failing here with "self-signed
# certificate in certificate chain" even though the host itself is fine. Appended to the image's
# own CA bundle via Debian's update-ca-certificates (not a wholesale replacement of it), so normal
# public-CA verification still works for anything that isn't actually Zscaler-intercepted.
#
# Pulled from a named build context (docker-compose.yml's additional_contexts, pointed at
# /opt/open-cti/tls -- runtime state, never this repo checkout) rather than COPYing it from
# anywhere inside this directory -- the cert never touches git, not even untracked in a
# gitignored folder. See README.md "TLS interception" for the full explanation and setup step.
#
# Deliberately exported for the rest of the build AND the running container, not just this one
# RUN step -- boto3 (AWS calls) and pycti's GraphQL client (requests, calling OPENCTI_URL) hit
# the exact same interception at runtime, not only pip at build time. Four separate env vars
# because pip/requests/botocore each resolve their own trust bundle independently and don't share
# one convention:
#   PIP_CERT           -- pip itself
#   REQUESTS_CA_BUNDLE  -- the `requests` library (pycti's HTTP client)
#   AWS_CA_BUNDLE       -- botocore/boto3 (does not fall back to REQUESTS_CA_BUNDLE)
#   SSL_CERT_FILE       -- the stdlib ssl module's default context, as a catch-all
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
