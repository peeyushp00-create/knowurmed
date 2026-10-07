"""Who can open which page. One table, checked for every role."""

from django.test import TestCase
from django.urls import reverse

from app.models import DOCTOR, MEDICINE, USER, Appointment

from .helpers import PASSWORD, make_admin, make_doctor, make_medicine, make_patient

ANON, ADMIN, DOCTOR_ROLE, PATIENT = 'anonymous', 'admin', 'doctor', 'patient'

# page -> roles allowed to open it (everyone else: anonymous -> login, others -> 403)
PAGES = {
    'adminindex': {ADMIN},
    'add_med': {ADMIN},
    'manage_doctor': {ADMIN},
    'view_user': {ADMIN},
    'complaints': {ADMIN},
    'feedback': {ADMIN},
    'appoint_manage': {ADMIN, DOCTOR_ROLE},
    'doctor_home': {DOCTOR_ROLE},
    'doc_med': {DOCTOR_ROLE},
    'schedule': {DOCTOR_ROLE},
    'doc_complaint': {DOCTOR_ROLE},
    'doc_feedback': {DOCTOR_ROLE},
    'doc_secure': {DOCTOR_ROLE},
    'user_home': {PATIENT},
    'prescription_upload': {PATIENT},
}
PUBLIC_PAGES = ['home', 'login', 'registration', 'doc_reg', 'search_med']


class AccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_admin()
        make_doctor()
        make_patient()

    def client_for(self, role):
        if role != ANON:
            self.assertTrue(self.client.login(username=role, password=PASSWORD))
        return self.client

    def test_every_protected_page(self):
        for role in (ANON, ADMIN, DOCTOR_ROLE, PATIENT):
            for page, allowed in PAGES.items():
                with self.subTest(role=role, page=page):
                    self.client.logout()
                    response = self.client_for(role).get(reverse(page))
                    if role in allowed:
                        self.assertEqual(response.status_code, 200)
                    elif role == ANON:
                        self.assertRedirects(response, f"{reverse('login')}?next={reverse(page)}")
                    else:
                        self.assertEqual(response.status_code, 403)

    def test_public_pages_open_to_everyone(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)

    def test_403_page_offers_a_way_back(self):
        self.client_for(PATIENT)
        response = self.client.get(reverse('adminindex'))
        self.assertContains(response, "You don't have access to this page", status_code=403)
        self.assertContains(response, reverse('user_home'), status_code=403)


class AdminActionTests(TestCase):
    """The original bug: these actions worked without logging in."""

    def setUp(self):
        self.pending_user, self.pending_profile = make_patient('newbie', status='Pending')
        self.pending_doctor = make_doctor('newdoc', status='Pending')
        self.medicine = make_medicine()

    def test_anonymous_cannot_approve_accounts_or_delete_medicines(self):
        self.client.post(reverse('view_user'), {'id': self.pending_profile.id, 'action': 'approve'})
        self.client.post(reverse('manage_doctor'), {'id': DOCTOR.objects.get().id, 'action': 'approve'})
        self.client.post(reverse('add_med'), {'action': 'delete', 'id': self.medicine.id})
        self.pending_profile.refresh_from_db()
        self.assertEqual(self.pending_profile.Approval_Status, 'Pending')
        self.assertEqual(DOCTOR.objects.get().Approval_Status, 'Pending')
        self.assertTrue(MEDICINE.objects.filter(pk=self.medicine.pk).exists())

    def test_patient_cannot_use_admin_actions(self):
        make_patient('pat')
        self.client.login(username='pat', password=PASSWORD)
        response = self.client.post(reverse('view_user'), {'id': self.pending_profile.id, 'action': 'approve'})
        self.assertEqual(response.status_code, 403)
        self.pending_profile.refresh_from_db()
        self.assertEqual(self.pending_profile.Approval_Status, 'Pending')

    def test_admin_can_approve_and_reject(self):
        make_admin()
        self.client.login(username='admin', password=PASSWORD)
        self.client.post(reverse('view_user'), {'id': self.pending_profile.id, 'action': 'approve'})
        self.client.post(reverse('manage_doctor'), {'id': DOCTOR.objects.get().id, 'action': 'reject'})
        self.pending_profile.refresh_from_db()
        self.assertEqual(self.pending_profile.Approval_Status, 'Approved')
        self.assertEqual(DOCTOR.objects.get().Approval_Status, 'Rejected')

    def test_admin_can_add_and_delete_medicines(self):
        make_admin()
        self.client.login(username='admin', password=PASSWORD)
        self.client.post(reverse('add_med'), {'medicine_name': 'Ibuprofen', 'generic_name': 'Ibuprofen'})
        self.assertTrue(MEDICINE.objects.filter(Medicine_name='Ibuprofen').exists())
        self.client.post(reverse('add_med'), {'action': 'delete', 'id': self.medicine.id})
        self.assertFalse(MEDICINE.objects.filter(pk=self.medicine.pk).exists())


class DoctorAppointmentTests(TestCase):
    def setUp(self):
        self.doc_a = make_doctor('doc_a')
        self.doc_b = make_doctor('doc_b')
        _, self.patient = make_patient()
        self.appt_b = Appointment.objects.create(
            user=self.patient, DOCTOR_ID=self.doc_b, date='2026-11-01', time='10:00', status='Pending',
        )

    def test_doctor_sees_and_changes_only_own_appointments(self):
        self.client.login(username='doc_a', password=PASSWORD)
        response = self.client.get(reverse('appoint_manage'))
        self.assertNotIn(self.appt_b, response.context['appointments'])
        self.client.post(reverse('appoint_manage'), {'id': self.appt_b.id, 'action': 'approve'})
        self.appt_b.refresh_from_db()
        self.assertEqual(self.appt_b.status, 'Pending')

        self.client.login(username='doc_b', password=PASSWORD)
        self.client.post(reverse('appoint_manage'), {'id': self.appt_b.id, 'action': 'approve'})
        self.appt_b.refresh_from_db()
        self.assertEqual(self.appt_b.status, 'Approved')


class RevokedAccessTests(TestCase):
    def test_rejected_after_login_loses_access_immediately(self):
        user, profile = make_patient()
        self.client.login(username='patient', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('user_home')).status_code, 200)

        USER.objects.filter(pk=profile.pk).update(Approval_Status='Rejected')
        response = self.client.get(reverse('user_home'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
