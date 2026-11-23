FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser && mkdir /app/data && chown appuser:appuser /app/data
COPY src/ /app/src/
COPY .streamlit/ /app/.streamlit/
USER appuser
EXPOSE 8501
CMD ["streamlit", "run", "src/kenworth/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
