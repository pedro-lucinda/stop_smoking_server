# Dockerfile
# 1. Use a slim Python base image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the dependency manifest first (leverages layer caching)
COPY requirements.txt .

# 4. Install Python dependencies without caching wheels
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Expose the port your FastAPI app will run on
EXPOSE 8000

# 7. Default command to start Uvicorn with your app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
