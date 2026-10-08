FROM python:3.12-slim-trixie

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends jq curl unzip fontconfig \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip \
  && unzip -q awscliv2.zip \
  && ./aws/install \
  && rm -rf aws awscliv2.zip

# Install Python deps in a layer that only rebuilds when requirements change.
COPY requirements.txt requirements-reports.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Package install is cheap (--no-deps); src/worker changes should not reinstall boto3, etc.
COPY setup.py ./
COPY src ./src
COPY pe_reports_django_project ./pe_reports_django_project
COPY worker ./worker
RUN pip install --no-cache-dir --no-deps .

ENV PYTHONPATH=/app/src:/app/pe_reports_django_project
ENV PE_API_URL=http://127.0.0.1:8000

RUN chmod +x worker/*.sh

CMD ["./worker/pe-worker-start.sh"]
