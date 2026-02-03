# Use official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Install system dependencies for OCR (EasyOCR/pdf2image)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy only the backend requirements first for caching
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY backend/ .

# Expose the port (Hugging Face uses 7860 by default)
EXPOSE 7860

# Run the application
# We use 0.0.0.0 to allow external connections in the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
