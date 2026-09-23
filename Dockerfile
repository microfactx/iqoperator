# IQOperator: bot Python + cockpit Next.js no mesmo container.
# Build determinístico (imune a trocas de builder Nixpacks/Railpack no Railway).
FROM node:20-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_OPTIONS=--max-old-space-size=1024 \
    NEXT_TELEMETRY_DISABLED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps Python primeiro (cache de layer)
COPY requirements.txt ./
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH=/opt/venv/bin:$PATH

# Deps Node + build do cockpit
COPY cockpit-next/package.json cockpit-next/package-lock.json ./cockpit-next/
RUN npm --prefix cockpit-next ci
COPY . ./
RUN mkdir -p data \
    && npm --prefix cockpit-next run build

EXPOSE 8080
CMD ["bash", "start.sh"]
