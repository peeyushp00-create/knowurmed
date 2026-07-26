from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import Prescription


class Command(BaseCommand):
    help = (
        "Deletes prescriptions (and their uploaded files) older than a given number of days. "
        "Not scheduled automatically — run manually or wire up to a scheduled task/cron yourself."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=30,
            help='Delete prescriptions last updated more than this many days ago (default: 30).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be deleted without deleting anything.',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        queryset = Prescription.objects.filter(updated_at__lt=cutoff)
        count = queryset.count()

        if options['dry_run']:
            self.stdout.write(f"Would delete {count} prescription(s) older than {options['days']} days.")
            return

        queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} prescription(s) older than {options['days']} days."))
