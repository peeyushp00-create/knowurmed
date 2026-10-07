"""One command to get a working local copy with data to click through.

    python manage.py setup_demo

Creates the database tables, loads the medicine catalog, and adds three
approved demo accounts (admin, doctor, patient) plus a little sample
activity so every dashboard has something on it. Safe to run again.
"""

from io import StringIO

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from app.models import DOCTOR, USER, Appointment
from app.models import complaints as Complaint
from app.models import feedback as Feedback
from app.permissions import ADMIN_GROUP, DOCTOR_GROUP, PATIENT_GROUP

DEMO_PASSWORD = 'KnowUrMed-demo'

ACCOUNTS = [
    ('admin', ADMIN_GROUP),
    ('doctor', DOCTOR_GROUP),
    ('patient', PATIENT_GROUP),
]


class Command(BaseCommand):
    help = 'Set up a local demo: database, medicine catalog and demo admin/doctor/patient accounts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Allow running with DEBUG off. Never use this on a real deployment.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'setup_demo creates accounts with a published password, so it only runs with DEBUG on.'
            )

        self.stdout.write('Creating database tables...')
        call_command('migrate', verbosity=0)

        self.stdout.write('Loading the medicine catalog...')
        call_command('seed_medicines', stdout=StringIO())

        users = {}
        for username, group_name in ACCOUNTS:
            user, created = User.objects.get_or_create(
                username=username, defaults={'email': f'{username}@example.com'},
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            user.groups.add(Group.objects.get_or_create(name=group_name)[0])
            users[username] = user

        doctor, _ = DOCTOR.objects.update_or_create(
            user_id=users['doctor'],
            defaults={
                'Name': 'Dr. Asha Menon',
                'Specialization': 'General Medicine',
                'Phone': '9800000001',
                'Email': 'doctor@example.com',
                'Approval_Status': 'Approved',
            },
        )
        patient, _ = USER.objects.update_or_create(
            user_id=users['patient'],
            defaults={
                'Age': '34',
                'Gender': 'Female',
                'phone': '9800000002',
                'email': 'patient@example.com',
                'Place': 'Kochi',
                'Approval_Status': 'Approved',
            },
        )

        if not Appointment.objects.filter(user=patient).exists():
            Appointment.objects.create(
                user=patient, DOCTOR_ID=doctor.user_id, date='2026-11-03', time='10:30', status='Approved',
            )
            Appointment.objects.create(
                user=patient, DOCTOR_ID=doctor.user_id, date='2026-11-17', time='16:00', status='Pending',
            )
        if not Complaint.objects.filter(user=patient).exists():
            Complaint.objects.create(
                user=patient, complaints='The appointment reminder email never arrived.', date='2026-10-01',
                reply='Thanks for reporting this, we are looking into it.',
            )
        if not Feedback.objects.filter(user=patient).exists():
            Feedback.objects.create(
                user=patient, feedback='The medicine safety cards are really easy to understand.', date='2026-10-02',
            )

        self.stdout.write(self.style.SUCCESS('\nDemo is ready. Start it with:  python manage.py runserver'))
        self.stdout.write('Then open http://127.0.0.1:8000/login and sign in as one of:\n')
        for username, _ in ACCOUNTS:
            self.stdout.write(f'  {username:<8} password: {DEMO_PASSWORD}')
