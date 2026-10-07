"""Registration, login and the approval flow."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app.models import DOCTOR, USER
from app.permissions import user_role

from .helpers import PASSWORD, make_admin, make_doctor, make_patient

GOOD_PASSWORD = 'Tea-garden-2026'


def patient_form(**overrides):
    data = {
        'username': 'meera', 'email': 'meera@example.com', 'phone': '9800000003', 'age': '29',
        'gender': 'Female', 'place': 'Kochi', 'password': GOOD_PASSWORD, 'confirm_password': GOOD_PASSWORD,
    }
    data.update(overrides)
    return data


def doctor_form(**overrides):
    data = {
        'username': 'drjoseph', 'name': 'Dr. Joseph', 'email': 'joseph@example.com', 'phone': '9800000004',
        'specialization': 'Cardiology', 'password': GOOD_PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationTests(TestCase):
    def test_patient_registration_creates_pending_patient(self):
        response = self.client.post(reverse('registration'), patient_form())
        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='meera')
        self.assertEqual(user_role(user), 'patient')
        self.assertEqual(USER.objects.get(user_id=user).Approval_Status, 'Pending')

    def test_doctor_registration_creates_pending_doctor(self):
        response = self.client.post(reverse('doc_reg'), doctor_form())
        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='drjoseph')
        self.assertEqual(user_role(user), 'doctor')
        doctor = DOCTOR.objects.get(user_id=user)
        self.assertEqual((doctor.Specialization, doctor.Approval_Status), ('Cardiology', 'Pending'))

    def test_rejects_weak_password(self):
        response = self.client.post(
            reverse('registration'), patient_form(password='12345678', confirm_password='12345678'), follow=True,
        )
        self.assertFalse(User.objects.filter(username='meera').exists())
        self.assertContains(response, 'This password is too common')

    def test_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('registration'), patient_form(confirm_password='different'), follow=True)
        self.assertFalse(User.objects.exists())
        self.assertContains(response, 'Passwords do not match')

    def test_rejects_duplicate_username_case_insensitive(self):
        make_patient('meera')
        response = self.client.post(reverse('registration'), patient_form(username='Meera'), follow=True)
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(response, 'already taken')

    def test_rejects_missing_fields_without_crashing(self):
        response = self.client.post(reverse('registration'), {'username': 'x'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please fill in')
        response = self.client.post(reverse('doc_reg'), {}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_rejects_bad_email_and_age(self):
        self.client.post(reverse('registration'), patient_form(email='not-an-email'))
        self.client.post(reverse('registration'), patient_form(age='-4'))
        self.assertFalse(User.objects.exists())


class LoginTests(TestCase):
    def login(self, username, password=PASSWORD):
        return self.client.post(reverse('login'), {'username': username, 'password': password})

    def test_each_role_lands_on_its_dashboard(self):
        make_admin()
        make_doctor()
        make_patient()
        for username, page in [('admin', 'adminindex'), ('doctor', 'doctor_home'), ('patient', 'user_home')]:
            with self.subTest(username=username):
                self.client.logout()
                self.assertRedirects(self.login(username), reverse(page))

    def test_pending_and_rejected_accounts_cannot_log_in(self):
        make_patient('waiting', status='Pending')
        make_doctor('refused', status='Rejected')
        response = self.client.post(reverse('login'), {'username': 'waiting', 'password': PASSWORD}, follow=True)
        self.assertContains(response, 'pending approval')
        response = self.client.post(reverse('login'), {'username': 'refused', 'password': PASSWORD}, follow=True)
        self.assertContains(response, 'not approved')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password(self):
        make_patient()
        response = self.login('patient', 'wrong')
        self.assertEqual(response.status_code, 401)
        self.assertContains(response, 'incorrect', status_code=401)

    def test_logout(self):
        make_patient()
        self.login('patient')
        self.assertRedirects(self.client.get(reverse('logout')), reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class PasswordChangeTests(TestCase):
    def test_doctor_changes_password_with_validation(self):
        user = make_doctor()
        self.client.login(username='doctor', password=PASSWORD)
        url = reverse('doc_secure')
        self.client.post(url, {'current_password': PASSWORD, 'new_password': '123', 'confirm_password': '123'})
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))

        self.client.post(url, {'current_password': PASSWORD, 'new_password': GOOD_PASSWORD,
                               'confirm_password': GOOD_PASSWORD})
        user.refresh_from_db()
        self.assertTrue(user.check_password(GOOD_PASSWORD))
