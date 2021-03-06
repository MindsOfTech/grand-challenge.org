###################
#  Base Container #
###################
ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION} as base

ARG GDCM_VERSION_TAG

# Build and install gdcm and install system dependencies
RUN apt-get update \
    && apt-get install -y \
        cmake \
        swig \
        python-openssl \
        libpng-dev \
        libjpeg-dev \
        libjpeg62-turbo-dev \
        libfreetype6-dev \
        libxft-dev \
        libffi-dev \
        wget \
        gettext \
        libopenslide-dev \
        libvips-dev \
    && mkdir -p /opt/gdcm/build \
    && cd /opt/gdcm \
    && git clone --branch v${GDCM_VERSION_TAG} --depth 1 git://git.code.sf.net/p/gdcm/gdcm \
    && cd /opt/gdcm/build \
    && cmake \
        -DCMAKE_SKIP_RPATH:BOOL=YES \
        -DCMAKE_INSTALL_PREFIX:PATH=/usr \
        -DGDCM_BUILD_SHARED_LIBS:BOOL=ON \
        -DGDCM_DOCUMENTATION:BOOL=OFF \
        -DGDCM_BUILD_DOCBOOK_MANPAGES:BOOL=OFF \
        -DGDCM_BUILD_TESTING:BOOL=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DGDCM_WRAP_PYTHON:BOOL=ON \
        -DGDCM_INSTALL_PYTHONMODULE_DIR=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
        -DGDCM_USE_VTK:BOOL=OFF \
        -DGDCM_USE_JPEGLS:BOOL=ON \
        -DGDCM_USE_PVRG:BOOL=ON \
        -DGDCM_USE_SYSTEM_EXPAT:BOOL=ON \
        -DGDCM_USE_SYSTEM_ZLIB:BOOL=ON \
        -DGDCM_USE_SYSTEM_UUID:BOOL=ON \
        -DGDCM_USE_SYSTEM_OPENJPEG:BOOL=ON \
        -DGDCM_USE_SYSTEM_OPENSSL:BOOL=ON \
        -DCMAKE_C_FLAGS=-fPIC \
        -DCMAKE_CXX_FLAGS=-fPIC \
        /opt/gdcm/gdcm \
    && make -j $(nproc) \
    && make install \
    && ldconfig \
    && rm -r /opt/gdcm \
    && apt-get purge -y swig cmake

ENV PYTHONUNBUFFERED 1

RUN mkdir -p /opt/poetry /app /static /opt/static \
    && python -m pip install -U "pip!=20.0" setuptools==45 \
    && python -m pip install -U poetry \
    && groupadd -r django && useradd -m -r -g django django \
    && chown django:django /opt/poetry /app /static /opt/static

# Install base python packages
COPY poetry.toml /opt/poetry
COPY pyproject.toml /opt/poetry
COPY poetry.lock /opt/poetry

WORKDIR /opt/poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

##################
# TEST CONTAINER #
##################
FROM base as test-base

# Add java and graphviz for plantuml documentation
RUN apt-get update && apt-get install -y default-jre graphviz
RUN poetry install --no-root
