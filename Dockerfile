FROM python:3.11-slim

RUN pip install --no-cache-dir requests

COPY notify.py /notify.py

ENTRYPOINT ["python", "/notify.py"]
