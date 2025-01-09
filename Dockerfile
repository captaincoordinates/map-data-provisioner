FROM ghcr.io/osgeo/gdal:ubuntu-small-3.10.0

RUN apt-get update --fix-missing \
  && apt-get install -y --no-install-recommends \
  python3-pip=24.0+dfsg-1ubuntu1.1 \
  && rm -rf /var/lib/apt/lists/*

COPY bc_trim_stitch/requirements-generated.txt /requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /requirements.txt
