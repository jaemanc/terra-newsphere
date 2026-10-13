#!/bin/sh
set -eu
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}" \
  --create --if-not-exists --topic news.raw --partitions 1 --replication-factor 1 \
  --config retention.ms=86400000 --config retention.bytes=536870912 \
  --config max.message.bytes=131072 --config segment.ms=3600000
