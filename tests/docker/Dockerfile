FROM rust:1.99.0-slim-bookworm@sha256:2c3a22f0a5533ea2dd5a16627bc841228151faa2d4de2644ac9987e4a2f1f2fa

ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl file git python3 time musl-tools zstd \
    && rm -rf /var/lib/apt/lists/*

RUN case "$TARGETARCH" in \
      arm64) rustup target add aarch64-unknown-linux-musl ;; \
      amd64) rustup target add x86_64-unknown-linux-musl ;; \
      *) exit 1 ;; \
    esac

# Both archives come from the same immutable compiler release; neither target
# may silently fall back to a different nightly.
RUN case "$TARGETARCH" in \
      arm64) asset=roc_nightly-linux_arm64-2026-10-09-258ab27.tar.gz; digest=9750ce89a820d3cdeadd751996d26c70b68584ca9428e52f43a1bb20702c54e5 ;; \
      amd64) asset=roc_nightly-linux_x86_64-2026-10-09-258ab27.tar.gz; digest=dcb99abdf17d062246c05e394357ad682b883a6bcff7b2e581e20564ea88ffc4 ;; \
      *) echo "Unsupported compiler architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl --fail --location --retry 3 "https://github.com/roc-lang/nightlies/releases/download/nightly-2026-10-09-258ab27/$asset" -o /tmp/roc.tar.gz \
    && echo "$digest  /tmp/roc.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/roc \
    && tar -xzf /tmp/roc.tar.gz -C /opt/roc --strip-components=1 \
    && rm /tmp/roc.tar.gz \
    && /opt/roc/roc version

RUN useradd --create-home --uid 1000 jlog \
    && mkdir -p /work/artifacts /work/cache /src \
    && chown -R jlog:jlog /work

ENV PATH="/opt/roc:${PATH}" ROC_CACHE_DIR=/work/cache CARGO_HOME=/work/cargo-cache PYTHONDONTWRITEBYTECODE=1
USER jlog
WORKDIR /src
CMD ["sleep", "infinity"]
