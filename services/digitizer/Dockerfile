FROM python:3.11-slim

# Pinned worker inputs. Keep in sync with docs/versions.lock.md.
ARG INKSTITCH_COMMIT=d22526223c2296044d9dd6145cc78de3bb0d5c75
ARG INKEX_COMMIT=a887f9d4c8adacd62786e4f46c8ef1467bedc1df

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STITCHORD_WORK_DIR=/tmp \
    STITCHORD_INKEX_PATH=/opt/inkex \
    STITCHORD_INKSTITCH_PATH=/opt/inkstitch

# wxPython imports GTK at import time even when no GUI is shown.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git libgtk-3-0 libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 libsdl2-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/inkstitch/inkstitch.git /opt/inkstitch \
    && git -C /opt/inkstitch checkout "${INKSTITCH_COMMIT}"
RUN git clone https://gitlab.com/CapellanCitizen/extensions.git /opt/inkex \
    && git -C /opt/inkex checkout "${INKEX_COMMIT}"

WORKDIR /app
COPY requirements-inkstitch.txt /tmp/requirements-inkstitch.txt
RUN pip install --no-cache-dir -r /tmp/requirements-inkstitch.txt

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
