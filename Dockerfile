FROM python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
WORKDIR /app
COPY probe_app.py .
RUN mkdir /state && chown 65534:65534 /state
USER 65534:65534
ENV PORT=8080 UNREADY_FILE=/state/unready LIVE_FAIL_FILE=/state/unlive
EXPOSE 8080
CMD ["python", "-I", "-B", "/app/probe_app.py"]
