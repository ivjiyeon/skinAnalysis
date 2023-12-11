FROM python:3.9

RUN pip install poetry
RUN poetry shell
RUN poetry install

ENV PORT 8080

CMD ["poetry", "run", "uvicorn", "web_api.main:app", "--port=8080"]