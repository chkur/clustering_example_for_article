FROM python:3.11

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED 1

RUN apt update && apt install libpq-dev python3-dev build-essential gdal-bin postgresql-client -y

RUN python -m pip install --upgrade pip
RUN pip install --upgrade pipenv
ADD . /usr/src/app
RUN pipenv install --system --deploy --dev