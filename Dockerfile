# The CLI chooses independent, pinned inputs for each edition.
ARG ALPINE_IMAGE
FROM ${ALPINE_IMAGE} AS runtime
ARG APK_PACKAGES
ARG FLAVOR
RUN apk add --no-cache ${APK_PACKAGES} \
    && mkdir -p /home/pi/.pi/agent /home/pi/.cache/node /workspace \
    && chown -R 1000:1000 /home/pi /workspace
COPY .build/${FLAVOR}/app/ /opt/pi/
COPY scripts/pi /usr/local/bin/pi
RUN chmod 755 /usr/local/bin/pi && chmod -R a+rX /opt/pi \
    && pi --version && pi --help >/dev/null
ENV HOME=/home/pi PI_OFFLINE=1 NODE_OPTIONS=--max-old-space-size=96 \
    NODE_COMPILE_CACHE=/home/pi/.cache/node TERM=xterm-256color
LABEL org.opencontainers.image.source="https://github.com/kengbailey/pi-oci" \
      org.opencontainers.image.title="Pi OCI" \
      org.opencontainers.image.description="Pi coding agent for ARMv7: Standard and OpenAI-only Minimal"
USER 1000:1000
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/pi"]
