"""One local Spark 4.0.2 application. No Spark master or distributed executors."""
import json
import logging
import os

from pydantic import ValidationError
from pyspark.sql import SparkSession

from terra_newsphere.normalize import normalize
from terra_newsphere.store import NewsStore

log = logging.getLogger("processor")


def write_batch(batch, batch_id):
    store = NewsStore()
    saved = rejected = 0
    try:
        # Input is capped by maxOffsetsPerTrigger. Do not collect an unbounded DataFrame.
        for row in batch.toLocalIterator():
            try:
                raw = json.loads(row.value)
                if not isinstance(raw, dict):
                    raise ValueError("Expected an object")
                article = normalize(raw, store.geography)
                saved += int(store.save(article))
            except (ValueError, TypeError, KeyError, ValidationError):
                rejected += 1
        log.info("Batch %s: saved=%d rejected=%d", batch_id, saved, rejected)
        # Storage failures propagate: Spark retries; atomic expiry-preserving writes are safe.
    finally:
        store.redis.close()


def main():
    logging.basicConfig(level=logging.INFO)
    master = os.environ.get("SPARK_MASTER", "local[1]")
    if master not in {"local[1]", "local[2]"}:
        raise ValueError("Only single-node local[1] or measured local[2] is supported")
    spark = (SparkSession.builder.appName("TerraNewsphere").master(master)
             .config("spark.sql.shuffle.partitions", "2")
             .config("spark.default.parallelism", "1")
             .config("spark.ui.enabled", "false")
             .config("spark.sql.streaming.minBatchesToRetain", "2")
             .config("spark.sql.streaming.numRecentProgressUpdates", "5")
             .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    incoming = (spark.readStream.format("kafka")
                .option("kafka.bootstrap.servers", os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
                .option("subscribe", os.environ.get("KAFKA_TOPIC", "news.raw"))
                .option("startingOffsets", "earliest")
                .option("failOnDataLoss", "true")
                .option("maxOffsetsPerTrigger", os.environ.get("SPARK_MAX_OFFSETS", "200"))
                .load().selectExpr("CAST(value AS STRING) AS value"))
    query = (incoming.writeStream.foreachBatch(write_batch)
             .option("checkpointLocation", os.environ.get("SPARK_CHECKPOINT", "/var/lib/terra/checkpoints/news"))
             .trigger(processingTime=f"{int(os.environ.get('SPARK_TRIGGER_SECONDS', '30'))} seconds")
             .start())
    try:
        query.awaitTermination()
    finally:
        query.stop()
        spark.stop()


if __name__ == "__main__":
    main()
