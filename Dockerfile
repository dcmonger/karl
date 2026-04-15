FROM python:3.11-slim
WORKDIR /app
COPY kitchen_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY kitchen_agent/ .
ENV PYTHONPATH=/app
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8000"]
