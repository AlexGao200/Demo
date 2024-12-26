FROM python:3.12.7

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app \
    PATH="/opt/poetry/bin:$PATH"

# Install project
RUN pip install poetry-plugin-export

COPY ./poetry.lock ./poetry.lock
COPY ./pyproject.toml ./pyproject.toml

RUN poetry export -f requirements.txt --output requirements.txt

RUN pip install -r requirements.txt

# Create non-root user
RUN useradd -ms /bin/sh -u 1001 app

# Set working directory and create it with proper permissions
WORKDIR /app
RUN chown app:app /app

RUN mkdir -p /app/tmp && chown -R app:app /app/tmp

# Copy only necessary directories for RAG evaluation
COPY --chown=app:app rag_eval ./rag_eval
COPY --chown=app:app services ./services
COPY --chown=app:app utils ./utils

# Switch to non-root user after installations
USER app

CMD ["python", "-m", "rag_eval.run_evals"]
