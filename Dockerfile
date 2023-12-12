FROM python:3.9

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false

RUN poetry install --no-dev --no-interaction --no-ansi

COPY . /app

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8000"]