FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN apt update && apt install -y build-essential portaudio19-dev

RUN --mount=type=cache,target=/root/.cache/pip python -m pip install /app

# The entry point will be set by the user when running the container
