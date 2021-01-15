FROM alpine

COPY scripts/entrypoint.sh /entrypoint.sh
COPY requirements.txt /requirements.txt

RUN \
    chmod +x /entrypoint.sh && \
    apk add --update --no-cache python3 python3-dev cmd:pip3 build-base ffmpeg && \
    pip3 install --upgrade pip && \
    pip3 install -r requirements.txt

CMD ["/entrypoint.sh"]
