FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp OMP_NUM_THREADS=1
COPY requirements-docker.lock /opt/ttb/requirements-docker.lock
RUN pip install --no-cache-dir -r /opt/ttb/requirements-docker.lock
COPY view_xlsx.py /opt/ttb/view_xlsx.py
WORKDIR /workspace
USER 1000:1000
CMD ["sleep", "infinity"]
