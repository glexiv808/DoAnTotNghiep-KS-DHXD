FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Copy requirements 
COPY requirements.txt .

# Cài đặt Dependency
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ML-app.py .

# Copy model files
COPY jupiter_notebook/model_ml.joblib /app/
COPY jupiter_notebook/model_logistic_regression.joblib /app/
COPY jupiter_notebook/model_random_forest.joblib /app/
COPY jupiter_notebook/model_xgboost.joblib /app/
COPY jupiter_notebook/scaler_logistic_regression.joblib /app/

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Run the application
CMD ["uvicorn", "ML-app:app", "--host", "0.0.0.0", "--port", "5000"]