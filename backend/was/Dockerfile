FROM python:3.12-slim-trixie

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    jq \
    libpq5 \
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
  && chmod +x worker/*.sh

ENV PYTHONPATH=/app/src:/app
ENV WAS_RESOURCE_ROOT=/WAS_REPORT_RESOURCES
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/was-matplotlib

ENTRYPOINT ["./worker/was-report-start.sh"]
