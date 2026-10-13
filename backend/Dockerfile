FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    libpango-1.0-0 libpangocairo-1.0-0 \
    libffi-dev shared-mime-info fonts-liberation \
    cron tzdata \
    && (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 \
        || apt-get install -y --no-install-recommends libgdk-pixbuf2.0-0) \
    # Police de la charte graphique pour les PDF d'export. Non bloquant : si le
    # paquet est introuvable, les PDF retombent sur Liberation (voir le
    # gabarit exports/rapport_patient.html).
    && (apt-get install -y --no-install-recommends fonts-ibm-plex \
        || echo "fonts-ibm-plex indisponible : PDF en Liberation") \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/cron/entrypoint.sh /app/cron/run_task.sh

EXPOSE 8000
