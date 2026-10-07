"""Prescription upload, OCR parsing, review and privacy."""

import io
import shutil
import tempfile
from pathlib import Path
from unittest import mock, skipUnless

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from app import ocr
from app.models import Prescription, PrescriptionItem

from .helpers import PASSWORD, make_medicine, make_patient

SAMPLE = Path(__file__).parent / 'data' / 'sample-prescription.png'


def png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (40, 40), 'white').save(buf, format='PNG')
    return buf.getvalue()


class OcrParsingTests(TestCase):
    def test_parse_line(self):
        self.assertEqual(
            ocr._parse_line('1. Paracetamol 500 mg twice a day for 5 days'),
            {'name_guess': 'Paracetamol', 'strength': '500 mg', 'frequency': 'twice a day', 'duration': 'for 5 days'},
        )
        self.assertEqual(ocr._parse_line('Tab. Metformin 500mg BD')['name_guess'], 'Metformin')
        self.assertEqual(ocr._parse_line('2) Cap Omeprazole 20 mg 1-0-1')['frequency'], '1-0-1')

    def test_match_medicine_is_fuzzy_but_never_invents(self):
        para = make_medicine('Paracetamol', 'Acetaminophen')
        self.assertEqual(ocr.match_medicine('Paracetmol'), para)  # OCR typo
        self.assertEqual(ocr.match_medicine('acetaminophen'.title()), para)
        self.assertIsNone(ocr.match_medicine('Dr. Asha Menon'))
        self.assertIsNone(ocr.match_medicine('ab'))

    def test_build_items_skips_headers(self):
        make_medicine('Amoxicillin', 'Amoxicillin')
        lines = [('City Care Clinic', 95), ('Amoxicillin 250 mg three times a day', 90), ('Review after one week', 90)]
        items = ocr.build_prescription_items(None, lines)
        self.assertEqual([(i.detected_name, i.detected_strength) for i in items], [('Amoxicillin', '250 mg')])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='knowurmed-test-media-'))
class UploadAndReviewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user, self.profile = make_patient()
        self.client.login(username='patient', password=PASSWORD)

    def upload(self, name='rx.png', content=None, content_type='image/png'):
        file = SimpleUploadedFile(name, content if content is not None else png_bytes(), content_type=content_type)
        return self.client.post(reverse('prescription_upload'), {'file': file})

    def test_rejects_wrong_type_and_fake_images(self):
        self.upload('rx.txt', b'hello', 'text/plain')
        self.upload('rx.png', b'not really a png')
        self.upload('rx.pdf', b'not a pdf', 'application/pdf')
        self.assertFalse(Prescription.objects.exists())

    @mock.patch('app.views.ocr.is_available', return_value=False)
    def test_upload_without_ocr_goes_to_manual_review(self, _):
        response = self.upload()
        prescription = Prescription.objects.get()
        self.assertRedirects(response, reverse('prescription_review', args=[prescription.id]))
        self.assertEqual(prescription.status, 'needs_review')

    def test_review_flow(self):
        with mock.patch('app.views.ocr.is_available', return_value=False):
            self.upload()
        prescription = Prescription.objects.get()
        url = reverse('prescription_review', args=[prescription.id])

        self.client.post(url, {'action': 'confirm_all'})
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, 'needs_review')  # nothing to confirm yet

        self.client.post(url, {'action': 'add_manual', 'manual_name': 'Ibuprofen', 'manual_strength': '200 mg'})
        item = PrescriptionItem.objects.get()
        self.assertTrue(item.is_manual and item.is_confirmed)

        self.client.post(url, {'action': 'confirm_all'})
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, 'confirmed')

    def test_other_patients_cannot_see_review_file_or_delete(self):
        with mock.patch('app.views.ocr.is_available', return_value=False):
            self.upload()
        prescription = Prescription.objects.get()
        file_id = prescription.files.get().id

        self.assertEqual(self.client.get(reverse('prescription_file_serve', args=[file_id])).status_code, 200)

        make_patient('nosy')
        self.client.login(username='nosy', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('prescription_review', args=[prescription.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse('prescription_file_serve', args=[file_id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('prescription_delete', args=[prescription.id])).status_code, 404)
        self.assertTrue(Prescription.objects.filter(pk=prescription.pk).exists())

    def test_owner_can_delete(self):
        with mock.patch('app.views.ocr.is_available', return_value=False):
            self.upload()
        prescription = Prescription.objects.get()
        self.assertEqual(self.client.get(reverse('prescription_delete', args=[prescription.id])).status_code, 405)
        self.client.post(reverse('prescription_delete', args=[prescription.id]))
        self.assertFalse(Prescription.objects.exists())

    @skipUnless(ocr.is_available(), 'Tesseract is not installed')
    def test_real_ocr_on_sample_prescription(self):
        for name, generic in [('Paracetamol', 'Acetaminophen'), ('Amoxicillin', 'Amoxicillin'),
                              ('Cetirizine', 'Cetirizine Hydrochloride')]:
            make_medicine(name, generic)
        self.upload('sample.png', SAMPLE.read_bytes())
        items = Prescription.objects.get().items.all()
        self.assertEqual(
            [(i.matched_medicine.Medicine_name, i.detected_strength, i.detected_frequency, i.detected_duration)
             for i in items],
            [('Paracetamol', '500 mg', 'twice a day', 'for 5 days'),
             ('Amoxicillin', '250 mg', 'three times a day', 'for 7 days'),
             ('Cetirizine', '10 mg', 'once a day', 'for 10 days')],
        )
