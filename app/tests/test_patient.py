"""Medicine search and the patient dashboard actions."""

from django.test import TestCase
from django.urls import reverse

from app.models import Appointment
from app.models import complaints as Complaint
from app.models import feedback as Feedback

from .helpers import PASSWORD, make_doctor, make_medicine, make_patient


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_medicine('Paracetamol', 'Acetaminophen')
        make_medicine('Ibuprofen', 'Ibuprofen')

    def test_search_by_brand_or_generic_name(self):
        for query in ('para', 'ACETAMIN'):
            with self.subTest(query=query):
                response = self.client.get(reverse('search_med'), {'q': query})
                self.assertEqual([m.Medicine_name for m in response.context['medicines']], ['Paracetamol'])

    def test_empty_search_shows_nothing(self):
        response = self.client.get(reverse('search_med'))
        self.assertEqual(list(response.context['medicines']), [])

    def test_autocomplete(self):
        data = self.client.get(reverse('search_med_autocomplete'), {'q': 'ib'}).json()
        self.assertEqual([r['name'] for r in data['results']], ['Ibuprofen'])
        self.assertEqual(self.client.get(reverse('search_med_autocomplete'), {'q': 'i'}).json(), {'results': []})


class PatientActionTests(TestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.pending_doctor = make_doctor('newdoc', status='Pending')
        self.user, self.profile = make_patient()
        self.client.login(username='patient', password=PASSWORD)

    def test_book_appointment_with_approved_doctor(self):
        data = {'doctor_id': self.doctor.pk, 'date': '2026-12-01', 'time': '11:00'}
        self.client.post(reverse('book_appointment'), data)
        appt = Appointment.objects.get()
        self.assertEqual((appt.user, appt.DOCTOR_ID, appt.status), (self.profile, self.doctor, 'Pending'))

    def test_cannot_book_unapproved_doctor_or_missing_time(self):
        self.client.post(reverse('book_appointment'), {'doctor_id': self.pending_doctor.pk, 'date': '2026-12-01',
                                                       'time': '11:00'})
        self.client.post(reverse('book_appointment'), {'doctor_id': self.doctor.pk, 'date': '', 'time': ''})
        self.assertFalse(Appointment.objects.exists())

    def test_state_changing_actions_require_post(self):
        for name in ('book_appointment', 'submit_complaint', 'submit_feedback'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 405)

    def test_complaint_and_feedback(self):
        self.client.post(reverse('submit_complaint'), {'complaint': 'Reminder email never came'})
        self.client.post(reverse('submit_feedback'), {'feedback': 'Very helpful'})
        self.client.post(reverse('submit_feedback'), {'feedback': '   '})
        self.assertEqual(Complaint.objects.get().user, self.profile)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_dashboard_lists_only_own_items(self):
        _, other = make_patient('other')
        Complaint.objects.create(user=other, complaints='not mine', date='2026-01-01', reply='')
        Complaint.objects.create(user=self.profile, complaints='mine', date='2026-01-01', reply='')
        response = self.client.get(reverse('user_home'))
        self.assertEqual([c.complaints for c in response.context['complaint_list']], ['mine'])
