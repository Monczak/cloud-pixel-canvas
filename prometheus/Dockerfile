FROM prom/prometheus:latest

USER root

COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY entrypoint.sh /etc/prometheus/entrypoint.sh

# Fix permissions
RUN chmod +x /etc/prometheus/entrypoint.sh && \
    chown -R nobody:nobody /etc/prometheus && \
    chown -R nobody:nobody /prometheus

USER nobody

ENTRYPOINT ["/etc/prometheus/entrypoint.sh"]

# Restore default command with arguments because ENTRYPOINT overrides CMD
CMD [ "--config.file=/etc/prometheus/prometheus.yml", \
      "--storage.tsdb.path=/prometheus", \
      "--web.console.libraries=/usr/share/prometheus/console_libraries", \
      "--web.console.templates=/usr/share/prometheus/consoles" ]
