FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860
WORKDIR /app

COPY frontend/gradio-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY frontend/gradio_app.py /app/gradio_app.py

EXPOSE 7860
CMD ["python", "gradio_app.py"]
