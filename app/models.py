import uuid

from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    category_name = models.CharField(max_length=255)


class DOCTOR(models.Model):
    user_id = models.OneToOneField(User,on_delete=models.CASCADE)
    Name = models.CharField(max_length=255)
    Specaialization = models.CharField(max_length=255)
    Phone = models.CharField(max_length=220)
    Email = models.EmailField()
    Approval_Status = models.CharField(max_length=50)
    reason = models.CharField(max_length=255, blank=True, null=True)


# class Category(models.Model):
#     category_name = models.CharField(max_length=255)


class USER(models.Model):
    user_id = models.OneToOneField(User,on_delete=models.CASCADE)
    Age= models.CharField(max_length=255)
    Gender = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    Place = models.CharField(max_length=50)
    reason = models.CharField(max_length=255, blank=True, null=True)
    Approval_Status = models.CharField(max_length=50, default='Pending')



class MEDICINE(models.Model):
    Medicine_name = models.CharField(max_length=255)
    Generic_Name = models.CharField(max_length=255)
    Composition = models.CharField(max_length=255)
    Indications = models.CharField(max_length=255)
    Dosage = models.CharField(max_length=255)
    Side_effects= models.CharField(max_length=255)
    reason = models.CharField(max_length=255, blank=True, null=True)
    Precautions = models.CharField(max_length=255)
    Drug_interactions = models.CharField(max_length=255)
    Manufacturer = models.CharField(max_length=255)

    # Extended safety / reference fields
    category = models.CharField(max_length=100, blank=True)
    prescription_required = models.BooleanField(default=False)
    mechanism = models.TextField(blank=True, help_text="How it works")
    food_guidance = models.TextField(blank=True)
    driving_warning = models.TextField(blank=True)
    pregnancy_info = models.TextField(blank=True)
    breastfeeding_info = models.TextField(blank=True)
    kidney_precaution = models.TextField(blank=True)
    liver_precaution = models.TextField(blank=True)
    storage_instructions = models.TextField(blank=True)
    missed_dose_guidance = models.TextField(blank=True)
    serious_warning_signs = models.TextField(blank=True)
    source_reference = models.CharField(max_length=500, blank=True)
    last_reviewed = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.Medicine_name


class MedicineSafetyNote(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('driving', 'Driving'),
        ('pregnancy', 'Pregnancy'),
        ('breastfeeding', 'Breastfeeding'),
        ('kidney', 'Kidney Conditions'),
        ('liver', 'Liver Conditions'),
        ('allergy', 'Allergies'),
        ('age', 'Age-Related Precautions'),
        ('interaction', 'Medicine Interactions'),
        ('duplicate', 'Duplicate Active Ingredients'),
    ]
    STATUS_CHOICES = [
        ('general_info', 'General Information'),
        ('low_concern', 'Low Concern'),
        ('caution', 'Caution'),
        ('important_warning', 'Important Warning'),
        ('review_required', 'Healthcare Review Required'),
        ('unavailable', 'Information Unavailable'),
    ]

    medicine = models.ForeignKey(MEDICINE, on_delete=models.CASCADE, related_name='safety_notes')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='unavailable')
    explanation = models.TextField(blank=True)
    recommended_action = models.TextField(blank=True)
    source_reference = models.CharField(max_length=500, blank=True)
    reviewed_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('medicine', 'category')

    def __str__(self):
        return f"{self.medicine.Medicine_name} - {self.get_category_display()}"



class Appointment(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    DOCTOR_ID =models.ForeignKey(User,on_delete=models.CASCADE)
    date= models.CharField(max_length=255)
    time = models.CharField(max_length=255)
    status = models.CharField(max_length=50)


def prescription_file_path(instance, filename):
    return f"prescriptions/{instance.prescription_id}/{uuid.uuid4().hex}_{filename}"


class Prescription(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('needs_review', 'Needs Review'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    patient = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='prescriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription #{self.pk} ({self.patient.user_id.username})"


class PrescriptionFile(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=prescription_file_path)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class OCRResult(models.Model):
    prescription_file = models.OneToOneField(PrescriptionFile, on_delete=models.CASCADE, related_name='ocr_result')
    raw_text = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    engine = models.CharField(max_length=50, default='tesseract')
    created_at = models.DateTimeField(auto_now_add=True)


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    detected_name = models.CharField(max_length=255, blank=True)
    detected_strength = models.CharField(max_length=100, blank=True)
    detected_form = models.CharField(max_length=100, blank=True)
    detected_frequency = models.CharField(max_length=100, blank=True)
    detected_duration = models.CharField(max_length=100, blank=True)
    ocr_confidence = models.FloatField(default=0)
    matched_medicine = models.ForeignKey(MEDICINE, on_delete=models.SET_NULL, null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return self.detected_name or "(manual entry)"


class complaints (models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    complaints = models.CharField(max_length=255)
    date= models.CharField(max_length=255)
    reply = models.CharField(max_length=255)


class feedback (models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    feedback = models.CharField(max_length=255)
    date= models.CharField(max_length=255)

