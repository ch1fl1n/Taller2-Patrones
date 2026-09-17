FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copiar el servicio y el shared al mismo nivel para que los imports funcionen
COPY . /app/services/account
COPY ../../shared /app/shared
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.account.main:app", "--host", "0.0.0.0", "--port", "8001"]
