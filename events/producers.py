"""
Kafka producer for the Admin & Vendor Service.

Design decisions:
- Singleton producer instance (thread-safe with confluent-kafka).
- All events include a standard envelope: eventId, eventType, timestamp, payload.
- Delivery failures are logged and re-raised so callers can handle them.
- Graceful shutdown via close() — called from Django AppConfig.ready() or signal handlers.
- Synchronous flush after each produce() call to ensure delivery before DB commit.
  This keeps it simple now; switch to async batched delivery when throughput requires it.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from django.conf import settings

logger = logging.getLogger(__name__)

_producer_instance = None


def _get_producer():
    """
    Lazy-initialise the Confluent Kafka producer singleton.
    Returns None if Kafka is not configured (allows tests to run without Kafka).
    """
    global _producer_instance
    if _producer_instance is not None:
        return _producer_instance

    bootstrap_servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", None)
    if not bootstrap_servers:
        logger.warning("KAFKA_BOOTSTRAP_SERVERS not configured. Kafka producer disabled.")
        return None

    try:
        from confluent_kafka import Producer
        config = settings.KAFKA_PRODUCER_CONFIG
        _producer_instance = Producer(config)
        logger.info("Kafka producer initialised. Brokers: %s", bootstrap_servers)
        return _producer_instance
    except Exception as exc:
        logger.error("Failed to initialise Kafka producer: %s", exc)
        return None


def _delivery_report(err, msg):
    """Callback invoked by librdkafka after each message delivery attempt."""
    if err is not None:
        logger.error(
            "Kafka delivery failed | topic=%s partition=%s offset=%s error=%s",
            msg.topic(), msg.partition(), msg.offset(), err,
        )
    else:
        logger.debug(
            "Kafka delivery OK | topic=%s partition=%s offset=%s",
            msg.topic(), msg.partition(), msg.offset(),
        )


def _build_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build the standard event envelope."""
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "payload": payload,
    }


def publish_event(topic: str, event_type: str, payload: Dict[str, Any], key: str = None) -> bool:
    """
    Publish a single event to a Kafka topic.

    Args:
        topic:      Kafka topic name (use KafkaTopics constants).
        event_type: Event type string (e.g. "product.created").
        payload:    Event payload dict.
        key:        Optional Kafka message key (e.g. product ID) for partitioning.

    Returns:
        True if the message was produced and flushed successfully.
        False if Kafka is unavailable (non-fatal — logged).

    Raises:
        RuntimeError: If the producer fails to flush within timeout.
    """
    producer = _get_producer()
    if producer is None:
        logger.warning(
            "Kafka producer unavailable. Event NOT published | topic=%s type=%s",
            topic, event_type,
        )
        return False

    event = _build_event(event_type, payload)
    message_bytes = json.dumps(event, default=str).encode("utf-8")
    message_key = key.encode("utf-8") if key else None

    try:
        producer.produce(
            topic=topic,
            value=message_bytes,
            key=message_key,
            on_delivery=_delivery_report,
        )
        # Flush synchronously — ensures the message is delivered before we return.
        # timeout=10 seconds; raises BufferError if the queue is full.
        unflushed = producer.flush(timeout=10)
        if unflushed > 0:
            raise RuntimeError(
                f"Kafka producer flush timeout: {unflushed} messages still in queue."
            )
        return True

    except Exception as exc:
        logger.error(
            "Failed to publish Kafka event | topic=%s type=%s error=%s",
            topic, event_type, exc,
        )
        raise


def close_producer():
    """
    Flush and close the producer.
    Call this on application shutdown.
    """
    global _producer_instance
    if _producer_instance is not None:
        logger.info("Flushing and closing Kafka producer...")
        _producer_instance.flush(timeout=30)
        _producer_instance = None
        logger.info("Kafka producer closed.")