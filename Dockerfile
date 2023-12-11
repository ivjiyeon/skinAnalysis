FROM python:3.9

RUN pip install poetry

WORKDIR /app
ADD . /app

RUN poetry install

ENV PORT 8080

CMD ["poetry", "run", "uvicorn", "web_api.main:app", "--port=8080"]