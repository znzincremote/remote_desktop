FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

CMD ["uvicorn", "signaling_server:app", "--host", "0.0.0.0", "--port", "8000"] 