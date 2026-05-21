FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py garmin_client.py ./

RUN mkdir -p /data/garmin_tokens /opt/data/fit_files \
    && chown -R appuser:appuser /data /opt/data

USER appuser

ENV GARMIN_TOKEN_STORE=/data/garmin_tokens \
    FIT_STORE_DIR=/opt/data/fit_files

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
