FROM debian:bookworm

# Native Debian wxPython (bookworm: 4.2.0) for Python 3.11. This avoids the
# Ubuntu wheel's libjpeg.so.8/libtiff.so.5 ABI mismatch entirely.
ARG INKSTITCH_COMMIT=d22526223c2296044d9dd6145cc78de3bb0d5c75
ARG INKEX_COMMIT=a887f9d4c8adacd62786e4f46c8ef1467bedc1df

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STITCHORD_WORK_DIR=/tmp \
    STITCHORD_INKEX_PATH=/opt/inkex \
    STITCHORD_INKSTITCH_PATH=/opt/inkstitch \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev \
        python3-wxgtk4.0 \
        git ca-certificates \
        libgtk-3-0 libglib2.0-0 libgl1 libnotify4 libsdl2-2.0-0 \
        glib-networking \
    && rm -rf /var/lib/apt/lists/*

# Use Debian's interpreter explicitly; the venv must see the apt wx package
# through /usr/lib/python3/dist-packages.
RUN /usr/bin/python3.11 -m venv --system-site-packages /opt/venv \
    && pip install --no-cache-dir --upgrade pip

RUN git clone https://github.com/inkstitch/inkstitch.git /opt/inkstitch \
    && git -C /opt/inkstitch checkout "${INKSTITCH_COMMIT}"
RUN git clone https://gitlab.com/CapellanCitizen/extensions.git /opt/inkex \
    && git -C /opt/inkex checkout "${INKEX_COMMIT}"

WORKDIR /app
COPY requirements-inkstitch.txt /tmp/requirements-inkstitch.txt
RUN grep -vi '^wxpython' /tmp/requirements-inkstitch.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && ! pip freeze | grep -qi '^wxpython' \
    && python -c "import wx; print('wx', wx.version())"

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Fail the image build, not the first request, if Ink/Stitch cannot import.
RUN cd /opt/inkstitch \
    && PYTHONPATH=/opt/inkex:/opt/inkstitch python -c \
       "from lib.elements import node_to_elements; from lib.tartan.palette import Palette; print('inkstitch import ok')"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
