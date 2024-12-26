FROM python:3.12

# Set working directory
WORKDIR /app

# Copy your requirements file (modify accordingly)
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy your test files and app code
COPY . .
