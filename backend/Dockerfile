FROM python:3.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PATH="/opt/poetry/bin:$PATH"

RUN pip install poetry-plugin-export

# Set working directory
WORKDIR /app

COPY ./poetry.lock ./poetry.lock
COPY ./pyproject.toml ./pyproject.toml

RUN poetry export -f requirements.txt --output requirements.txt

RUN pip install -r requirements.txt

RUN mkdir -p /app/tmp

# Copy project files
COPY . .

COPY .env .env

# Download NLTK data with retry mechanism
RUN python3 -c "import nltk; nltk.download('punkt', quiet=True)" || \
    python3 -c "import nltk; nltk.download('punkt', quiet=True)" || \
    python3 -c "import nltk; nltk.download('punkt', quiet=True)"

EXPOSE 5000

# Run gunicorn
#ENTRYPOINT ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:create_app()"]
ENTRYPOINT ["poetry", "run", "gunicorn", "--worker-class", "gevent", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:create_app()"]

