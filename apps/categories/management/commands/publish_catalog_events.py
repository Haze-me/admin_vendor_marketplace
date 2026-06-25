"""
Management command: publish_catalog_events

Re-publishes every existing category (as category.created) and every
existing product (as product.created) to Kafka so the catalog read-model
can be fully reconciled / backfilled.

Usage:
    python manage.py publish_catalog_events              # categories + products
    python manage.py publish_catalog_events --only categories
    python manage.py publish_catalog_events --only products
    python manage.py publish_catalog_events --dry-run    # log payloads, no Kafka
"""
import logging

from django.core.management.base import BaseCommand

from apps.categories.models import Category
from apps.products.models import Product
from apps.products.services import _build_product_payload
from events.producers import publish_event
from events.topics import KafkaTopics

logger = logging.getLogger(__name__)


def _category_payload(category: Category) -> dict:
    return {
        "categoryId": str(category.id),
        "name": category.name,
        "description": category.description,
        "slug": category.slug,
        "parentId": str(category.parent.id) if category.parent else None,
        "isActive": category.is_active,
    }


class Command(BaseCommand):
    help = (
        "Re-publish all existing categories and/or products as Kafka events "
        "so the catalog-service read-model can be backfilled."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only",
            choices=["categories", "products"],
            default=None,
            help="Publish only categories or only products (default: both).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log what would be published without actually sending to Kafka.",
        )

    def handle(self, *args, **options):
        only = options["only"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no messages will be sent to Kafka."))

        do_categories = only in (None, "categories")
        do_products = only in (None, "products")

        if do_categories:
            self._publish_categories(dry_run)

        if do_products:
            self._publish_products(dry_run)

        self.stdout.write(self.style.SUCCESS("Done."))

    def _publish_categories(self, dry_run: bool):
        categories = Category.objects.select_related("parent").order_by("created_at")
        total = categories.count()
        self.stdout.write(f"Publishing {total} categories as category.created ...")

        ok = fail = 0
        for cat in categories.iterator():
            payload = _category_payload(cat)
            if dry_run:
                self.stdout.write(f"  [DRY RUN] category.created id={cat.id} name={cat.name!r}")
                ok += 1
                continue
            try:
                publish_event(
                    topic=KafkaTopics.CATEGORY_CREATED,
                    event_type=KafkaTopics.CATEGORY_CREATED,
                    payload=payload,
                    key=str(cat.id),
                )
                ok += 1
            except Exception as exc:
                self.stderr.write(f"  FAILED category id={cat.id} name={cat.name!r}: {exc}")
                logger.error("publish_catalog_events: category %s failed: %s", cat.id, exc)
                fail += 1

        self.stdout.write(
            self.style.SUCCESS(f"  Categories: {ok} published, {fail} failed.")
        )

    def _publish_products(self, dry_run: bool):
        products = (
            Product.objects
            .select_related("vendor", "category")
            .prefetch_related("product_images")
            .order_by("created_at")
        )
        total = products.count()
        self.stdout.write(f"Publishing {total} products as product.created ...")

        ok = fail = 0
        for product in products.iterator(chunk_size=100):
            payload = _build_product_payload(product)
            if dry_run:
                self.stdout.write(f"  [DRY RUN] product.created id={product.id} name={product.name!r}")
                ok += 1
                continue
            try:
                publish_event(
                    topic=KafkaTopics.PRODUCT_CREATED,
                    event_type=KafkaTopics.PRODUCT_CREATED,
                    payload=payload,
                    key=str(product.id),
                )
                ok += 1
            except Exception as exc:
                self.stderr.write(f"  FAILED product id={product.id} name={product.name!r}: {exc}")
                logger.error("publish_catalog_events: product %s failed: %s", product.id, exc)
                fail += 1

        self.stdout.write(
            self.style.SUCCESS(f"  Products: {ok} published, {fail} failed.")
        )
