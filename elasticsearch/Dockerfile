# Use the official Elasticsearch image
FROM docker.elastic.co/elasticsearch/elasticsearch:8.15.0

# Set environment variables
ENV discovery.type=single-node
ENV bootstrap.memory_lock=true
ENV xpack.license.self_generated.type=basic
ENV xpack.security.enabled=false
ENV xpack.security.http.ssl.enabled=false

# Generate self-signed SSL certificate
RUN elasticsearch-certutil cert -out /usr/share/elasticsearch/config/elastic-certificates.p12 -pass ""

# Set permissions for the certificate
RUN chown elasticsearch:elasticsearch /usr/share/elasticsearch/config/elastic-certificates.p12

# Expose the necessary ports
EXPOSE 9200 9300

# Set up healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -fsSL http://localhost:9200/_cluster/health || exit 1

# Run Elasticsearch as non-root user
USER elasticsearch

# Run Elasticsearch
CMD ["elasticsearch"]
