FROM ghcr.io/osgeo/gdal:ubuntu-small-3.10.0

RUN apt-get update --fix-missing \
  && apt-get install -y --no-install-recommends \
  python3-pip=24.0+dfsg-1ubuntu1.1 \
  && rm -rf /var/lib/apt/lists/*

COPY mdp_common/requirements-generated.txt /requirements-common.txt
RUN pip install --no-cache-dir --break-system-packages -r /requirements-common.txt
COPY mdp_bc_hillshade/requirements-generated.txt /requirements-bc_hillshade.txt
RUN pip install --no-cache-dir --break-system-packages -r /requirements-bc_hillshade.txt
COPY mdp_bc_trim/requirements-generated.txt /requirements-bc_trim.txt
RUN pip install --no-cache-dir --break-system-packages -r /requirements-bc_trim.txt
COPY mdp_canvec/requirements-generated.txt /requirements-canvec.txt
RUN pip install --no-cache-dir --break-system-packages -r /requirements-canvec.txt

COPY mdp_common /mdp_common
RUN pip install --no-cache-dir --break-system-packages -e /mdp_common
COPY mdp_bc_hillshade /mdp_bc_hillshade
RUN pip install --no-cache-dir --break-system-packages -e mdp_bc_hillshade
COPY mdp_bc_trim /mdp_bc_trim
RUN pip install --no-cache-dir --break-system-packages -e mdp_bc_trim
COPY mdp_canvec /mdp_canvec
RUN pip install --no-cache-dir --break-system-packages -e mdp_canvec
