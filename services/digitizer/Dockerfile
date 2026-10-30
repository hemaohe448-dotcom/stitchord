FROM python:3.11-slim

# Pinned worker inputs. Keep in sync with docs/versions.lock.md.
ARG INKSTITCH_COMMIT=d22526223c2296044d9dd6145cc78de3bb0d5c75
ARG INKEX_COMMIT=a887f9d4c8adacd62786e4f46c8ef1467bedc1df
# No 4.3.2 Linux wheel exists; 4.2.5 is the newest cp311 wheel. Use the
# Ubuntu 22.04 build (glibc 2.35) so it stays compatible with the Debian
# bookworm base (glibc 2.36); Ubuntu 24.04 wheels need newer glibc.
ARG WX_VERSION=4.2.5

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STITCHORD_WORK_DIR=/tmp \
    STITCHORD_INKEX_PATH=/opt/inkex \
    STITCHORD_INKSTITCH_PATH=/opt/inkstitch

# wxPython imports GTK at import time even when no GUI is shown.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git libgtk-3-0 libglib2.0-0 libgl1 libglu1-mesa libsm6 libxext6 libxrender1 \
        libsdl2-2.0-0 libnotify4 libjpeg62-turbo libtiff6 libpng16-16 libwebp7 \
        libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/inkstitch/inkstitch.git /opt/inkstitch \
    && git -C /opt/inkstitch checkout "${INKSTITCH_COMMIT}"
RUN git clone https://gitlab.com/CapellanCitizen/extensions.git /opt/inkex \
    && git -C /opt/inkex checkout "${INKEX_COMMIT}"

WORKDIR /app
COPY requirements-inkstitch.txt /tmp/requirements-inkstitch.txt
RUN grep -vi '^wxpython' /tmp/requirements-inkstitch.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir \
        --find-links=https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04/ \
        "wxPython==${WX_VERSION}"

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
