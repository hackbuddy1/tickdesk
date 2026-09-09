FROM timescale/timescaledb:latest-pg16

RUN apk add --no-cache --virtual .build-deps \
        git build-base postgresql16-dev \
 && git clone --branch v0.8.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
 && cd /tmp/pgvector \
 && make OPTFLAGS="" with_llvm=no \
 && make install with_llvm=no \
 && rm -rf /tmp/pgvector \
 && apk del .build-deps