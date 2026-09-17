FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/services/risk
COPY ../../shared /app/shared
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.risk.main:app", "--host", "0.0.0.0", "--port", "8002"]
