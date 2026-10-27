FROM python:3.12.13-slim-trixie@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    jq \
    libpq5 \
    postgresql-client \
    qpdf \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-plain-generic \
    texlive-xetex \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY setup.py ./
COPY schema ./schema
COPY src ./src
COPY worker ./worker

RUN pip install --no-cache-dir --no-deps . \
  && mkdir -p /output /WAS_REPORT_RESOURCES \
  && cp -R /app/src/was_reports/resources/. /WAS_REPORT_RESOURCES/ \
  && chmod -R a+rX /app/src /app/schema /app/worker /WAS_REPORT_RESOURCES \
  && chmod +x /app/worker/*.sh \
  && groupadd --system --gid 10001 was-reporting \
  && useradd --system --uid 10001 --gid was-reporting --home-dir /nonexistent \
    --shell /usr/sbin/nologin was-reporting \
  && chown -R was-reporting:was-reporting /output /WAS_REPORT_RESOURCES

ENV PYTHONPATH=/app/src:/app
ENV WAS_RESOURCE_ROOT=/WAS_REPORT_RESOURCES
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/was-matplotlib

USER was-reporting

ENTRYPOINT ["./worker/was-report-start.sh"]
