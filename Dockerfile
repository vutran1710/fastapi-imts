FROM python:3.9-alpine

RUN apk add gcc python3-dev musl-dev

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install pipenv

COPY Pipfile* .

RUN pipenv install --deploy

COPY . .

EXPOSE 5000

CMD pipenv run uvicorn main:app --host 0.0.0.0 --port 5000
