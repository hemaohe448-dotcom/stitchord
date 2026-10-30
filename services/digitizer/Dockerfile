FROM python:3.11-slim

# Pinned worker inputs. Keep in sync with docs/versions.lock.md.
ARG INKSTITCH_COMMIT=d22526223c2296044d9dd6145cc78de3bb0d5c75
ARG INKEX_COMMIT=a887f9d4c8adacd62786e4f46c8ef1467bedc1df
# No 4.3.2 Linux wheel exists; 4.2.5 is the newest cp311 wheel.
ARG WX_VERSION=4.2.5

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STITCHORD_WORK_DIR=/tmp \
    STITCHORD_INKEX_PATH=/opt/inkex \
    STITCHORD_INKSTITCH_PATH=/opt/inkstitch

# wxPython imports GTK/X11 at import time even when no GUI is shown.
# The wx wheel is built on Ubuntu 22.04; Debian has libjpeg.so.62/libtiff.so.6,
# so install the Ubuntu 22.04 compatibility libs (jpeg8/tiff5) explicitly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git curl libgtk-3-0 libglib2.0-0 libgl1 libglu1-mesa libsm6 libxext6 libxrender1 \
        libsdl2-2.0-0 libnotify4 libjpeg62-turbo libtiff6 libwebp7 \
        libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
        libxtst6 libxi6 libxcursor1 libxrandr2 libxinerama1 libxfixes3 \
        libxcomposite1 libxdamage1 libxkbcommon0 libxkbcommon-x11-0 \
    && curl -fsSL -o /tmp/libjpeg8.deb \
        http://archive.ubuntu.com/ubuntu/pool/main/libj/libjpeg-turbo/libjpeg-turbo8_2.1.2-0ubuntu1_amd64.deb \
    && curl -fsSL -o /tmp/libtiff5.deb \
        http://archive.ubuntu.com/ubuntu/pool/main/t/tiff/libtiff5_4.3.0-6ubuntu0.13_amd64.deb \
    && dpkg -i --force-depends /tmp/libjpeg8.deb /tmp/libtiff5.deb \
    && ldconfig \
    && rm -f /tmp/libjpeg8.deb /tmp/libtiff5.deb \
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
