FROM python:3.8-alpine

COPY requirements.txt .
# create user and install requirements
RUN adduser -D -h /app exporter && \
    pip install -r requirements.txt --no-cache-dir && \
    rm /requirements.txt

WORKDIR /app
USER exporter
# copy app
COPY --chown=exporter:exporter . /app

# port hint
EXPOSE 8000
