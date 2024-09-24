ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

#RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
#    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project


COPY . ./
RUN mkdir config
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["uv", "run", "talesbot"]
