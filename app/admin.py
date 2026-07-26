from django.contrib import admin

from .models import Category, DOCTOR, USER, MEDICINE, Appointment, MedicineSafetyNote
from .models import complaints as Complaint, feedback as Feedback

admin.site.register(Category)
admin.site.register(DOCTOR)
admin.site.register(USER)
admin.site.register(MEDICINE)
admin.site.register(MedicineSafetyNote)
admin.site.register(Appointment)
admin.site.register(Complaint)
admin.site.register(Feedback)
