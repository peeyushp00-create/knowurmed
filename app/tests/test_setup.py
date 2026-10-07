"""The one-command demo setup and the role-group migration."""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from app.models import MEDICINE
from app.permissions import user_role


@override_settings(DEBUG=True)
class SetupDemoTests(TestCase):
    def test_creates_working_demo_accounts_and_is_repeatable(self):
        call_command('setup_demo', stdout=StringIO())
        call_command('setup_demo', stdout=StringIO())  # second run must not fail or duplicate
        self.assertGreaterEqual(MEDICINE.objects.count(), 10)
        for username, page in [('admin', 'adminindex'), ('doctor', 'doctor_home'), ('patient', 'user_home')]:
            with self.subTest(username=username):
                self.assertEqual(user_role(User.objects.get(username=username)), username)
                self.client.logout()
                response = self.client.post(reverse('login'), {'username': username, 'password': 'KnowUrMed-demo'})
                self.assertRedirects(response, reverse(page))
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)

    @override_settings(DEBUG=False)
    def test_refuses_to_run_in_production(self):
        with self.assertRaises(CommandError):
            call_command('setup_demo', stdout=StringIO())
