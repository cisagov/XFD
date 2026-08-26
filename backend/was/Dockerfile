FROM python:3.12-slim-trixie

WORKDIR /app

ENV WAS_GENERATE_REPORT_SRC=/usr/src/was-generate-report

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    jq \
    libpq5 \
    qpdf \
    texlive-fonts-recommended \
    texlive-xetex \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY setup.py ./
COPY reporting.py wasMailerController.py wasReportController.py ./
COPY schema ./schema
COPY src ./src
COPY was_report ./was_report
COPY worker ./worker

RUN pip install --no-cache-dir --no-deps . \
  && mkdir -p /WAS_REPORT_GENERATION/docs \
    /WAS_REPORT_GENERATION/assets/fonts \
  && cp -R /app/was_report/. /WAS_REPORT_GENERATION/ \
  && chmod +x worker/*.sh

ENV PYTHONPATH=/app/src:/app
ENV WAS_CONFIG_PATH=/app/was_config.txt

ENTRYPOINT ["./worker/was-report-start.sh"]
