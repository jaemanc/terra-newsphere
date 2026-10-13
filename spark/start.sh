#!/bin/sh
set -eu
exec spark-submit --master "${SPARK_MASTER:-local[1]}" \
  --driver-memory "${SPARK_DRIVER_MEMORY:-768m}" \
  --conf spark.jars.ivy=/opt/spark-ivy \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 \
  /app/spark/main.py
