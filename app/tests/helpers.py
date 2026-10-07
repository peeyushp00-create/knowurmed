from django.contrib.auth.models import Group, User

from app.models import DOCTOR, MEDICINE, USER
from app.permissions import ADMIN_GROUP, DOCTOR_GROUP, PATIENT_GROUP

PASSWORD = 'Str0ng-test-pass'


def make_admin(username='admin'):
    user = User.objects.create_user(username=username, password=PASSWORD)
    user.groups.add(Group.objects.get_or_create(name=ADMIN_GROUP)[0])
    return user


def make_doctor(username='doctor', status='Approved'):
    user = User.objects.create_user(username=username, password=PASSWORD)
    user.groups.add(Group.objects.get_or_create(name=DOCTOR_GROUP)[0])
    DOCTOR.objects.create(
        user_id=user, Name=f'Dr {username}', Specialization='General Medicine',
        Phone='1', Email=f'{username}@example.com', Approval_Status=status,
    )
    return user


def make_patient(username='patient', status='Approved'):
    user = User.objects.create_user(username=username, password=PASSWORD)
    user.groups.add(Group.objects.get_or_create(name=PATIENT_GROUP)[0])
    profile = USER.objects.create(
        user_id=user, Age='30', Gender='Female', phone='1', email=f'{username}@example.com',
        Place='Kochi', Approval_Status=status,
    )
    return user, profile


def make_medicine(name='Paracetamol', generic='Acetaminophen'):
    return MEDICINE.objects.create(
        Medicine_name=name, Generic_Name=generic, Composition='', Indications='', Dosage='',
        Side_effects='', Precautions='', Drug_interactions='', Manufacturer='',
    )
