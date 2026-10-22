FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000 BARIA_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home baria && mkdir /data && chown baria:baria /data
COPY app.py web.py serve.py config.py ./
COPY engine/ ./engine/
COPY static/ ./static/
COPY data/memoria.json data/regras.json ./data/
USER baria
EXPOSE 8000
CMD ["python", "serve.py"]
