FROM jupyter/scipy-notebook:python-3.11

USER ${NB_UID}
WORKDIR /workspace

COPY docker/notebook/requirements.txt /tmp/geocausal-notebook-requirements.txt
RUN mamba install -y -c conda-forge \
    sqlite=3.53.2 \
    libsqlite=3.53.2 \
    "statsmodels>=0.14.5" \
    geopandas \
    shapely \
    pyproj \
    fiona \
    pyogrio \
    rasterio \
    folium \
    branca \
    mapclassify \
    matplotlib \
    openpyxl \
 && mamba clean --all -f -y \
 && python -m pip install --no-cache-dir -r /tmp/geocausal-notebook-requirements.txt

ENV PYTHONPATH=/workspace
ENV PROJ_DATA=/opt/conda/share/proj
ENV PROJ_LIB=/opt/conda/share/proj
ENV GDAL_DATA=/opt/conda/share/gdal
ENV JUPYTER_TOKEN=geocausal
