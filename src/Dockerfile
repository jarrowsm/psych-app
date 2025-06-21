FROM python:latest

WORKDIR /psych_app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --no-create-home appuser && \
    chown -R appuser:appuser /psych_app
USER appuser

ENTRYPOINT ["python", "server.py"]

