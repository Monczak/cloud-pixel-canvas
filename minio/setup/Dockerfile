FROM minio/mc:latest

COPY setup.sh /usr/bin/setup.sh
RUN chmod +x /usr/bin/setup.sh

ENTRYPOINT ["/usr/bin/setup.sh"]
