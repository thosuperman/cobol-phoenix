# COBOL Phoenix sandbox runner: GnuCOBOL + a tiny Python job runner.
# Runs as an unprivileged user; intended to be started with no network,
# a read-only root filesystem, dropped capabilities and resource limits.
FROM python:3.13.17-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends gnucobol make \
 && rm -rf /var/lib/apt/lists/* \
 && cobc --version | head -1

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin runner \
 && mkdir -p /jobs && chown 10001:10001 /jobs
COPY phoenix_runner.py /opt/phoenix/phoenix_runner.py

USER 10001
WORKDIR /home/runner
ENTRYPOINT ["python", "-I", "/opt/phoenix/phoenix_runner.py"]
CMD ["serve", "/jobs"]
