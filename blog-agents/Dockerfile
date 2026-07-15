FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OUTPUT_DIR=/data/output
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app /srv/app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=10s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn","app.server:app","--host","0.0.0.0","--port","8000"]
