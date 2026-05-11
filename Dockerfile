FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app/backend \
    DJANGO_SETTINGS_MODULE=config.settings

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Build args for CRA (baked into bundle at build time)
ARG REACT_APP_API_URL
ARG REACT_APP_STRIPE_PUBLISHABLE_KEY
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_STRIPE_PUBLISHABLE_KEY=$REACT_APP_STRIPE_PUBLISHABLE_KEY

# Frontend build
COPY frontend/package*.json /app/frontend/
RUN cd /app/frontend && npm install
COPY frontend/ /app/frontend/
RUN cd /app/frontend && npm run build

# Backend
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/

# Copy CRA build output into staticfiles so WhiteNoise can serve it
RUN mkdir -p /app/backend/staticfiles/frontend && \
    cp -r /app/frontend/build/. /app/backend/staticfiles/frontend/

WORKDIR /app/backend
RUN python manage.py collectstatic --noinput

EXPOSE 8080
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT"]
