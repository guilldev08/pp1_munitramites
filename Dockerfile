FROM python:3.11-slim

# libfbclient2: librería nativa del cliente Firebird que carga firebird-driver
RUN apt-get update \
    && apt-get install -y --no-install-recommends libfbclient2 \
    && ln -sf /usr/lib/x86_64-linux-gnu/libfbclient.so.2 /usr/lib/x86_64-linux-gnu/libfbclient.so \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
