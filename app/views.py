import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import ocr
from .models import (
    DOCTOR,
    MEDICINE,
    USER,
    Appointment,
    Prescription,
    PrescriptionFile,
    PrescriptionItem,
)
from .models import complaints as Complaint
from .models import feedback as Feedback
from .permissions import (
    ADMIN,
    DOCTOR_GROUP,
    HOME_FOR_ROLE,
    PATIENT,
    PATIENT_GROUP,
    is_approved,
    role_profile,
    role_required,
    user_role,
)
from .permissions import (
    DOCTOR as DOCTOR_ROLE,
)

# ---------------------------------------------------------------- helpers


def _patient_profile(request):
    return USER.objects.filter(user_id=request.user).first()


def _registration_errors(data, required, password, confirm=None, user=None):
    """Validate a registration form; returns a list of messages (empty = valid)."""
    errors = []
    missing = [label for field, label in required if not data.get(field, '').strip()]
    if missing:
        errors.append(f"Please fill in: {', '.join(missing)}.")
    username = data.get('username', '').strip()
    if username and User.objects.filter(username__iexact=username).exists():
        errors.append('That username is already taken.')
    email = data.get('email', '').strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append('Please enter a valid email address.')
    if confirm is not None and password != confirm:
        errors.append('Passwords do not match.')
    if password:
        try:
            validate_password(password, user=user)
        except ValidationError as err:
            errors.extend(err.messages)
    return errors


# ---------------------------------------------------------------- public pages


def home(request):
    return render(request, 'home.html')


def login(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Username or password incorrect.')
            return render(request, 'login_page.html', status=401)

        role = user_role(user)
        if role is None:
            messages.error(request, 'This account has no role assigned. Please contact the administrator.')
            return redirect('login')
        if role != ADMIN:
            profile = role_profile(user, role)
            if profile is None:
                messages.error(request, 'Account profile not found. Please contact the administrator.')
                return redirect('login')
            if profile.Approval_Status == 'Rejected':
                messages.error(request, 'Your registration was not approved.')
                return redirect('login')
            if not is_approved(user, role):
                messages.error(request, 'Your registration is pending approval.')
                return redirect('login')

        auth_login(request, user)
        return redirect(HOME_FOR_ROLE[role])
    return render(request, 'login_page.html')


def logout_view(request):
    auth_logout(request)
    return redirect('home')


def registration(request):
    if request.method == "POST":
        data = request.POST
        password = data.get('password', '')
        required = [
            ('username', 'username'), ('email', 'email'), ('phone', 'phone'), ('age', 'age'),
            ('gender', 'gender'), ('place', 'place'), ('password', 'password'),
        ]
        errors = _registration_errors(data, required, password, data.get('confirm_password', ''))
        age = data.get('age', '').strip()
        if age and (not age.isdigit() or not 0 < int(age) < 130):
            errors.append('Please enter a valid age.')
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('registration')

        user = User.objects.create_user(
            username=data['username'].strip(), password=password, email=data['email'].strip(),
        )
        user.groups.add(Group.objects.get_or_create(name=PATIENT_GROUP)[0])
        USER.objects.create(
            user_id=user,
            Age=age,
            Gender=data['gender'],
            phone=data['phone'].strip(),
            email=data['email'].strip(),
            Place=data['place'].strip(),
            Approval_Status='Pending',
        )
        messages.success(request, 'Registration completed. Please wait for admin approval.')
        return redirect('login')

    return render(request, 'registration.html')


def doc_reg(request):
    if request.method == "POST":
        data = request.POST
        password = data.get('password', '')
        required = [
            ('username', 'username'), ('name', 'name'), ('email', 'email'), ('phone', 'phone'),
            ('specialization', 'specialization'), ('password', 'password'),
        ]
        confirm = data.get('confirm_password') if 'confirm_password' in data else None
        errors = _registration_errors(data, required, password, confirm)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('doc_reg')

        user = User.objects.create_user(
            username=data['username'].strip(), password=password, email=data['email'].strip(),
        )
        user.groups.add(Group.objects.get_or_create(name=DOCTOR_GROUP)[0])
        DOCTOR.objects.create(
            user_id=user,
            Name=data['name'].strip(),
            Specialization=data['specialization'].strip(),
            Phone=data['phone'].strip(),
            Email=data['email'].strip(),
            Approval_Status='Pending',
        )
        messages.success(request, 'Registration completed. Please wait for admin approval.')
        return redirect('login')

    return render(request, 'doc_reg.html')


def search_med(request):
    query = request.GET.get('q', '').strip()
    if query:
        medicines = MEDICINE.objects.filter(
            Q(Medicine_name__icontains=query) | Q(Generic_Name__icontains=query)
        ).prefetch_related('safety_notes').order_by('Medicine_name')
    else:
        medicines = MEDICINE.objects.none()
    return render(request, 'search_med.html', {'medicines': medicines, 'query': query})


def search_med_autocomplete(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        matches = MEDICINE.objects.filter(
            Q(Medicine_name__icontains=query) | Q(Generic_Name__icontains=query)
        ).order_by('Medicine_name')[:8]
        results = [
            {'name': m.Medicine_name, 'generic_name': m.Generic_Name, 'category': m.category}
            for m in matches
        ]
    return JsonResponse({'results': results})


# ---------------------------------------------------------------- admin


@role_required(ADMIN)
def adminindex(request):
    return render(request, 'adminindex.html')


@role_required(ADMIN)
def add_med(request):
    if request.method == "POST":
        if request.POST.get('action') == 'delete':
            MEDICINE.objects.filter(pk=request.POST.get('id')).delete()
            messages.success(request, 'Medicine deleted')
        else:
            name = request.POST.get('medicine_name', '').strip()
            if not name:
                messages.error(request, 'Medicine name is required.')
                return redirect('add_med')
            MEDICINE.objects.create(
                Medicine_name=name,
                Generic_Name=request.POST.get('generic_name', ''),
                Composition=request.POST.get('composition', ''),
                Indications=request.POST.get('indications', ''),
                Dosage=request.POST.get('dosage', ''),
                Side_effects=request.POST.get('side_effects', ''),
                Precautions=request.POST.get('precautions', ''),
                Drug_interactions=request.POST.get('drug_interactions', ''),
                Manufacturer=request.POST.get('manufacturer', ''),
            )
            messages.success(request, 'Medicine added')
        return redirect('add_med')

    return render(request, 'add_med.html', {'medicines': MEDICINE.objects.all()})


def _set_status(request, model, ok_message_by_action, redirect_to):
    obj = model.objects.filter(pk=request.POST.get('id')).first()
    action = request.POST.get('action')
    new_status = {'approve': 'Approved', 'reject': 'Rejected'}.get(action)
    if obj and new_status:
        obj.Approval_Status = new_status
        obj.save(update_fields=['Approval_Status'])
        messages.success(request, ok_message_by_action[action])
    return redirect(redirect_to)


@role_required(ADMIN)
def manage_doctor(request):
    if request.method == "POST":
        labels = {'approve': 'Doctor approved', 'reject': 'Doctor rejected'}
        return _set_status(request, DOCTOR, labels, 'manage_doctor')
    return render(request, 'manage_doctor.html', {'doctors': DOCTOR.objects.all()})


@role_required(ADMIN)
def view_user(request):
    if request.method == "POST":
        return _set_status(request, USER, {'approve': 'User approved', 'reject': 'User rejected'}, 'view_user')
    return render(request, 'view_user.html', {'users': USER.objects.all()})


@role_required(ADMIN)
def complaints(request):
    if request.method == "POST":
        complaint = Complaint.objects.filter(pk=request.POST.get('id')).first()
        if complaint:
            complaint.reply = request.POST.get('reply', '')
            complaint.save()
            messages.success(request, 'Reply sent')
        return redirect('complaints')

    return render(request, 'complaints.html', {'complaint_list': Complaint.objects.all().order_by('-id')})


@role_required(ADMIN)
def feedback(request):
    return render(request, 'feedback.html', {'feedback_list': Feedback.objects.all().order_by('-id')})


@role_required(ADMIN, DOCTOR_ROLE)
def appoint_manage(request):
    # Doctors only ever see and change their own appointments; admins see all.
    appointments = Appointment.objects.all()
    if request.role == DOCTOR_ROLE:
        appointments = appointments.filter(DOCTOR_ID=request.user)

    if request.method == "POST":
        appt = appointments.filter(pk=request.POST.get('id')).first()
        new_status = {'approve': 'Approved', 'decline': 'Declined'}.get(request.POST.get('action'))
        if appt and new_status:
            appt.status = new_status
            appt.save(update_fields=['status'])
            messages.success(request, f'Appointment {new_status.lower()}')
        return redirect('appoint_manage')

    return render(request, 'appoint_manage.html', {'appointments': appointments.order_by('-id')})


# ---------------------------------------------------------------- doctor


@role_required(DOCTOR_ROLE)
def doctor_home(request):
    return render(request, 'doctor_home.html')


@role_required(DOCTOR_ROLE)
def doc_med(request):
    return render(request, 'doc_med.html', {'medicines': MEDICINE.objects.all()})


@role_required(DOCTOR_ROLE)
def schedule(request):
    appointments = Appointment.objects.filter(DOCTOR_ID=request.user, status='Approved').order_by('date', 'time')
    return render(request, 'schedule.html', {'appointments': appointments})


@role_required(DOCTOR_ROLE)
def doc_complaint(request):
    if request.method == "POST":
        complaint = Complaint.objects.filter(pk=request.POST.get('id')).first()
        if complaint:
            complaint.reply = request.POST.get('reply', '')
            complaint.save()
            messages.success(request, 'Reply sent')
        return redirect('doc_complaint')

    return render(request, 'doc_complaint.html', {'complaint_list': Complaint.objects.all().order_by('-id')})


@role_required(DOCTOR_ROLE)
def doc_feedback(request):
    return render(request, 'doc_feedback.html', {'feedback_list': Feedback.objects.all().order_by('-id')})


@role_required(DOCTOR_ROLE)
def doc_secure(request):
    if request.method == "POST":
        current = request.POST.get('current_password', '')
        new = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect')
        elif new != confirm:
            messages.error(request, 'New passwords do not match')
        else:
            try:
                validate_password(new, user=request.user)
            except ValidationError as err:
                for message in err.messages:
                    messages.error(request, message)
                return redirect('doc_secure')
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password updated successfully')
        return redirect('doc_secure')

    return render(request, 'doc_secure.html')


# ---------------------------------------------------------------- patient


@role_required(PATIENT)
def user_home(request):
    profile = _patient_profile(request)
    context = {
        'profile': profile,
        'doctors': DOCTOR.objects.filter(Approval_Status='Approved'),
        'appointments': Appointment.objects.filter(user=profile).order_by('-id'),
        'complaint_list': Complaint.objects.filter(user=profile).order_by('-id'),
        'feedback_list': Feedback.objects.filter(user=profile).order_by('-id'),
        'prescriptions': Prescription.objects.filter(patient=profile).order_by('-created_at'),
    }
    return render(request, 'user_home.html', context)


@require_POST
@role_required(PATIENT)
def book_appointment(request):
    profile = _patient_profile(request)
    # Only approved doctors can be booked.
    doctor = DOCTOR.objects.filter(user_id__pk=request.POST.get('doctor_id'), Approval_Status='Approved').first()
    date, time = request.POST.get('date', '').strip(), request.POST.get('time', '').strip()
    if not doctor or not date or not time:
        messages.error(request, 'Please choose a doctor, a date and a time.')
        return redirect('user_home')
    Appointment.objects.create(user=profile, DOCTOR_ID=doctor.user_id, date=date, time=time, status='Pending')
    messages.success(request, 'Appointment requested')
    return redirect('user_home')


@require_POST
@role_required(PATIENT)
def submit_complaint(request):
    text = request.POST.get('complaint', '').strip()
    if text:
        Complaint.objects.create(
            user=_patient_profile(request), complaints=text, date=timezone.now().strftime('%Y-%m-%d'), reply='',
        )
        messages.success(request, 'Complaint submitted')
    return redirect('user_home')


@require_POST
@role_required(PATIENT)
def submit_feedback(request):
    text = request.POST.get('feedback', '').strip()
    if text:
        Feedback.objects.create(
            user=_patient_profile(request), feedback=text, date=timezone.now().strftime('%Y-%m-%d'),
        )
        messages.success(request, 'Feedback submitted')
    return redirect('user_home')


# ---------------------------------------------------------------- prescriptions (patient only)

ALLOWED_PRESCRIPTION_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}


def _validate_prescription_upload(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    content_type = ALLOWED_PRESCRIPTION_TYPES.get(ext)
    if not content_type:
        return None, 'Unsupported file type. Please upload a JPG, PNG, or PDF.'

    if uploaded_file.size > settings.PRESCRIPTION_MAX_UPLOAD_SIZE:
        return None, 'File is too large. Maximum size is 10 MB.'

    header = uploaded_file.read(8)
    uploaded_file.seek(0)
    if content_type == 'application/pdf':
        if not header.startswith(b'%PDF'):
            return None, 'This file does not look like a valid PDF.'
    else:
        try:
            from PIL import Image
            img = Image.open(uploaded_file)
            img.verify()
            uploaded_file.seek(0)
        except Exception:
            return None, 'This file does not look like a valid image.'

    return content_type, None


def _own_prescription(request, prescription_id):
    """The prescription if it belongs to the logged-in patient; 404 otherwise (never 403, to not reveal it exists)."""
    return get_object_or_404(Prescription, pk=prescription_id, patient=_patient_profile(request))


@role_required(PATIENT)
def prescription_upload(request):
    if request.method == "POST":
        profile = _patient_profile(request)
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'Please choose a file to upload.')
            return redirect('prescription_upload')

        content_type, error = _validate_prescription_upload(uploaded_file)
        if error:
            messages.error(request, error)
            return redirect('prescription_upload')

        prescription = Prescription.objects.create(patient=profile, status='processing')
        prescription_file = PrescriptionFile.objects.create(
            prescription=prescription,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            content_type=content_type,
            size_bytes=uploaded_file.size,
        )

        if not ocr.is_available():
            prescription.status = 'needs_review'
            messages.info(
                request,
                'Automatic reading is not set up on this server, '
                'so please add the medicines from your prescription below.',
            )
        else:
            try:
                ocr_result = ocr.process_prescription_file(prescription_file)
                prescription.status = 'needs_review'
                if ocr_result.confidence < ocr.LOW_CONFIDENCE_THRESHOLD or not prescription.items.exists():
                    messages.warning(
                        request,
                        "We couldn't read this prescription clearly. Please add your medicines manually below.",
                    )
            except Exception:
                prescription.status = 'failed'
                messages.error(
                    request,
                    'We were unable to process this file. Please try a clearer photo or a different format.',
                )
        prescription.save()

        return redirect('prescription_review', prescription_id=prescription.id)

    return render(request, 'prescription_upload.html', {'ocr_available': ocr.is_available()})


@role_required(PATIENT)
def prescription_review(request, prescription_id):
    prescription = _own_prescription(request, prescription_id)

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'update_item':
            item = get_object_or_404(PrescriptionItem, pk=request.POST.get('item_id'), prescription=prescription)
            item.detected_name = request.POST.get('detected_name', item.detected_name)
            item.detected_strength = request.POST.get('detected_strength', item.detected_strength)
            item.detected_form = request.POST.get('detected_form', item.detected_form)
            item.detected_frequency = request.POST.get('detected_frequency', item.detected_frequency)
            item.detected_duration = request.POST.get('detected_duration', item.detected_duration)
            item.is_edited = True
            item.is_confirmed = True
            item.save()
            messages.success(request, 'Medicine updated and confirmed.')

        elif action == 'confirm_item':
            item = get_object_or_404(PrescriptionItem, pk=request.POST.get('item_id'), prescription=prescription)
            item.is_confirmed = True
            item.save()

        elif action == 'remove_item':
            PrescriptionItem.objects.filter(pk=request.POST.get('item_id'), prescription=prescription).delete()
            messages.success(request, 'Medicine removed from this prescription.')

        elif action == 'add_manual':
            name = request.POST.get('manual_name', '').strip()
            if name:
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    detected_name=name,
                    detected_strength=request.POST.get('manual_strength', ''),
                    detected_frequency=request.POST.get('manual_frequency', ''),
                    detected_duration=request.POST.get('manual_duration', ''),
                    matched_medicine=ocr.match_medicine(name),
                    is_manual=True,
                    is_confirmed=True,
                    position=prescription.items.count(),
                )
                messages.success(request, 'Medicine added.')

        elif action == 'confirm_all':
            if prescription.items.exists() and not prescription.items.filter(is_confirmed=False).exists():
                prescription.status = 'confirmed'
                prescription.save()
                messages.success(request, 'All medicines confirmed.')
            else:
                messages.error(request, 'Please confirm or remove every detected medicine first.')

        return redirect('prescription_review', prescription_id=prescription.id)

    prescription_file = prescription.files.order_by('-uploaded_at').first()
    context = {
        'prescription': prescription,
        'prescription_file': prescription_file,
        'ocr_result': getattr(prescription_file, 'ocr_result', None) if prescription_file else None,
        'items': prescription.items.all(),
        'all_confirmed': prescription.items.exists() and not prescription.items.filter(is_confirmed=False).exists(),
    }
    return render(request, 'prescription_review.html', context)


@role_required(PATIENT)
def prescription_file_serve(request, file_id):
    prescription_file = get_object_or_404(PrescriptionFile, pk=file_id, prescription__patient=_patient_profile(request))
    return FileResponse(prescription_file.file.open('rb'), content_type=prescription_file.content_type)


@require_POST
@role_required(PATIENT)
def prescription_delete(request, prescription_id):
    _own_prescription(request, prescription_id).delete()
    messages.success(request, 'Prescription deleted.')
    return redirect('user_home')
