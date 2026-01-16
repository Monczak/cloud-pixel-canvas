FROM alpine:latest

RUN apk add --no-cache curl jq
COPY setup.sh /setup.sh
RUN chmod +x /setup.sh

CMD ["/setup.sh"]
