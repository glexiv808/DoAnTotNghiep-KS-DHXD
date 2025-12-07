FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Copy requirements 
COPY requirements.txt .

# Cài đặt Dependency
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code

COPY ML-app.py .

COPY jupiter_notebook/model_ml.joblib /app/
# Copy model_ml.joblib file vào COntainer

# Expose port
EXPOSE 5000



# Run the application
CMD ["python", "app.py"]