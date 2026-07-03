from django.core.management.base import BaseCommand
from django.db.models import Q

from catalog.models import Flower
from catalog.thumbnails import render_thumbnail


class Command(BaseCommand):
    help = "Generate a color-coded placeholder thumbnail for any Flower missing one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Regenerate thumbnails for every flower, even ones that already have one.",
        )

    def handle(self, *args, **options):
        flowers = (
            Flower.objects.all()
            if options["all"]
            else Flower.objects.filter(Q(image="") | Q(image__isnull=True))
        )
        count = 0
        for flower in flowers:
            content = render_thumbnail(flower)
            flower.image.save(content.name, content, save=True)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Generated {count} thumbnail(s)."))
