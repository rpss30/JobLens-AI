FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# The base image lags Debian security updates, so patched OS packages are pulled
# in at build time. Without the upgrade the image ships whatever was current when
# the base tag was published, and the container scan fails on fixes that exist.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip setuptools==83.0.0 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

COPY . .

EXPOSE 8501
EXPOSE 8000
EXPOSE 8001

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
