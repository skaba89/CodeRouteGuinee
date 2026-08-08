FROM python:3.12-slim

WORKDIR /opt/coderoute-edge
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/coderoute-edge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY coderoute_edge/ ./coderoute_edge/

RUN useradd -m -u 1001 edgeuser \
    && mkdir -p /var/lib/coderoute-edge \
    && chown -R edgeuser:edgeuser /opt/coderoute-edge /var/lib/coderoute-edge
USER edgeuser

EXPOSE 8443
VOLUME ["/var/lib/coderoute-edge"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,ssl,urllib.request; p=os.getenv('CODEROUTE_EDGE_BIND_PORT','8443'); insecure=os.getenv('CODEROUTE_EDGE_ALLOW_INSECURE_HTTP','').lower() in ('1','true','yes','on'); scheme='http' if insecure else 'https'; ctx=ssl._create_unverified_context() if scheme=='https' else None; urllib.request.urlopen(f'{scheme}://127.0.0.1:{p}/health', context=ctx, timeout=3).read()" || exit 1

CMD ["python", "-m", "coderoute_edge"]
