from django.contrib import admin

from .models import (
    DOCTOR,
    MEDICINE,
    USER,
    Appointment,
    Category,
    MedicineSafetyNote,
    OCRResult,
    Prescription,
    PrescriptionFile,
    PrescriptionItem,
)
from .models import complaints as Complaint
from .models import feedback as Feedback

admin.site.register(Category)
admin.site.register(DOCTOR)
admin.site.register(USER)
admin.site.register(MEDICINE)
admin.site.register(MedicineSafetyNote)
admin.site.register(Appointment)
admin.site.register(Complaint)
admin.site.register(Feedback)
admin.site.register(Prescription)
admin.site.register(PrescriptionFile)
admin.site.register(OCRResult)
admin.site.register(PrescriptionItem)
