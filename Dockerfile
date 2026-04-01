FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r projects/agrostima-scout/requirements.txt

WORKDIR /app/projects/agrostima-scout

CMD ["python", "main.py"]
