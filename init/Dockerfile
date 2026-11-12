FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssl     && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir cryptography

COPY generate-secrets.sh /generate-secrets.sh
RUN chmod +x /generate-secrets.sh

ENTRYPOINT ["/generate-secrets.sh"]
