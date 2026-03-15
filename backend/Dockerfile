FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    cmake ninja-build libssl-dev git build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --branch 0.15.0 https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && cmake -S /tmp/liboqs -B /tmp/liboqs/build -GNinja \
       -DBUILD_SHARED_LIBS=ON -DOQS_BUILD_ONLY_LIB=ON \
    && cmake --build /tmp/liboqs/build \
    && cmake --install /tmp/liboqs/build \
    && ldconfig \
    && rm -rf /tmp/liboqs

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LD_LIBRARY_PATH=/usr/local/lib

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
