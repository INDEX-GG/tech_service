FROM python:3.10.9-slim-buster

COPY ./requirements.txt /src/requirements.txt

RUN pip install -U pip && \
    pip install --no-cache-dir -r /src/requirements.txt

COPY . /src
ENV PATH "$PATH:/src/scripts"

RUN useradd -m -d /src -s /bin/bash app \
    && chown -R app:app /src/* && chmod +x /src/scripts/*

WORKDIR /src

CMD ["./scripts/start-prod.sh"]