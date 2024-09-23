ARG PYTHON_VERSION=3.12.4

FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

ENV PYTHONBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY . ./
COPY src .
RUN mkdir config
CMD ["python", "-m", "talesbot"]
