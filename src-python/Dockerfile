FROM python:3.14-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simple-web-server.py .
COPY credentials /secrets/credentials

EXPOSE 8080

CMD ["python", "simple-web-server.py"]
