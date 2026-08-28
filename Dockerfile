FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
ENV PORT=8000
CMD gunicorn myproject.wsgi:application --bind 0.0.0.0:${PORT}
