FROM python:3.11.7-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_HOME /usr/local

RUN apt-get update && \
    apt-get install -y curl

RUN curl -sSL https://install.python-poetry.org | python3

COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-root --no-dev
WORKDIR /app
COPY . .

RUN mkdir -p /app/logs
CMD ["poetry", "run", "python", "manage.py", "collectstatic", "--noinput"]
CMD ["poetry", "run", "gunicorn", "sms_produce.wsgi", "-b", "0.0.0.0:8000"]