from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User, Group
from django.utils import timezone

from . import ocr
from .models import (
    Category, DOCTOR, USER, MEDICINE, Appointment,
    Prescription, PrescriptionFile, PrescriptionItem,
)
from .models import complaints as Complaint, feedback as Feedback


def home(request):
    return render(request, 'home.html')


def login(request):
    if request.method == "POST":
        uname = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=uname, password=password)

        if user is not None:
            if user.is_superuser or user.groups.filter(name='admin').exists():
                auth_login(request, user)
                return redirect('adminindex')

            elif user.groups.filter(name='docter').exists():
                doctor = DOCTOR.objects.filter(user_id=user).first()
                if doctor is None:
                    messages.error(request, 'Doctor profile not found')
                    return redirect('login')
                if doctor.Approval_Status == 'Approved':
                    auth_login(request, user)
                    return redirect('doctor_home')
                messages.error(request, 'Your registration is pending approval.')
                return redirect('login')

            elif user.groups.filter(name='user').exists():
                profile = USER.objects.filter(user_id=user).first()
                if profile is None:
                    messages.error(request, 'User profile not found')
                    return redirect('login')
                if profile.Approval_Status == 'Approved':
                    auth_login(request, user)
                    return redirect('user_home')
                messages.error(request, 'Your registration is pending approval.')
                return redirect('login')

            else:
                messages.error(request, 'Invalid username or password')
                return redirect('login')
        else:
            messages.error(request, 'Username or password incorrect')
    return render(request, 'login_page.html')


def logout_view(request):
    auth_logout(request)
    return redirect('home')


def registration(request):
    if request.method == "POST":
        username = request.POST['username']
        gender = request.POST['gender']
        age = request.POST['age']
        place = request.POST['place']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return redirect('registration')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('registration')

        user = User.objects.create_user(username=username, password=password, email=email)

        group, _ = Group.objects.get_or_create(name='user')
        user.groups.add(group)

        USER.objects.create(
            user_id=user,
            Age=age,
            Gender=gender,
            phone=phone,
            email=email,
            Place=place,
            Approval_Status='Pending',
        )

        messages.success(request, 'Registration completed. Please wait for admin approval.')
        return redirect('login')

    return render(request, 'registration.html')


def doc_reg(request):
    if request.method == "POST":
        username = request.POST['username']
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        specialization = request.POST['specialization']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('doc_reg')

        user = User.objects.create_user(username=username, password=password, email=email)

        group, _ = Group.objects.get_or_create(name='docter')
        user.groups.add(group)

        DOCTOR.objects.create(
            user_id=user,
            Name=name,
            Specaialization=specialization,
            Phone=phone,
            Email=email,
            Approval_Status='Pending',
        )

        messages.success(request, 'Registration completed. Please wait for admin approval.')
        return redirect('login')

    return render(request, 'doc_reg.html')


def adminindex(request):
    return render(request, 'adminindex.html')


def add_med(request):
    if request.method == "POST":
        if request.POST.get('action') == 'delete':
            MEDICINE.objects.filter(pk=request.POST.get('id')).delete()
            messages.success(request, 'Medicine deleted')
        else:
            MEDICINE.objects.create(
                Medicine_name=request.POST.get('medicine_name', ''),
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


def manage_doctor(request):
    if request.method == "POST":
        doctor = DOCTOR.objects.filter(pk=request.POST.get('id')).first()
        action = request.POST.get('action')
        if doctor and action == 'approve':
            doctor.Approval_Status = 'Approved'
            doctor.save()
            messages.success(request, 'Doctor approved')
        elif doctor and action == 'reject':
            doctor.Approval_Status = 'Rejected'
            doctor.save()
            messages.success(request, 'Doctor rejected')
        return redirect('manage_doctor')

    return render(request, 'manage_doctor.html', {'doctors': DOCTOR.objects.all()})


def view_user(request):
    if request.method == "POST":
        profile = USER.objects.filter(pk=request.POST.get('id')).first()
        action = request.POST.get('action')
        if profile and action == 'approve':
            profile.Approval_Status = 'Approved'
            profile.save()
            messages.success(request, 'User approved')
        elif profile and action == 'reject':
            profile.Approval_Status = 'Rejected'
            profile.save()
            messages.success(request, 'User rejected')
        return redirect('view_user')

    return render(request, 'view_user.html', {'users': USER.objects.all()})


def complaints(request):
    if request.method == "POST":
        complaint = Complaint.objects.filter(pk=request.POST.get('id')).first()
        if complaint:
            complaint.reply = request.POST.get('reply', '')
            complaint.save()
            messages.success(request, 'Reply sent')
        return redirect('complaints')

    return render(request, 'complaints.html', {'complaint_list': Complaint.objects.all().order_by('-id')})


def feedback(request):
    return render(request, 'feedback.html', {'feedback_list': Feedback.objects.all().order_by('-id')})


def appoint_manage(request):
    if request.method == "POST":
        appt = Appointment.objects.filter(pk=request.POST.get('id')).first()
        action = request.POST.get('action')
        if appt and action == 'approve':
            appt.status = 'Approved'
            appt.save()
            messages.success(request, 'Appointment approved')
        elif appt and action == 'decline':
            appt.status = 'Declined'
            appt.save()
            messages.success(request, 'Appointment declined')
        return redirect('appoint_manage')

    if request.user.is_authenticated and request.user.groups.filter(name='docter').exists():
        appointments = Appointment.objects.filter(DOCTOR_ID=request.user).order_by('-id')
    else:
        appointments = Appointment.objects.all().order_by('-id')
    return render(request, 'appoint_manage.html', {'appointments': appointments})


def doctor_home(request):
    return render(request, 'docter_home.html')


def doc_med(request):
    return render(request, 'doc_med.html', {'medicines': MEDICINE.objects.all()})


def schedule(request):
    if not request.user.is_authenticated:
        return redirect('login')
    appointments = Appointment.objects.filter(DOCTOR_ID=request.user, status='Approved').order_by('date', 'time')
    return render(request, 'schedule.html', {'appointments': appointments})


def doc_complaint(request):
    if request.method == "POST":
        complaint = Complaint.objects.filter(pk=request.POST.get('id')).first()
        if complaint:
            complaint.reply = request.POST.get('reply', '')
            complaint.save()
            messages.success(request, 'Reply sent')
        return redirect('doc_complaint')

    return render(request, 'doc_complaint.html', {'complaint_list': Complaint.objects.all().order_by('-id')})


def doc_feedback(request):
    return render(request, 'doc_feedback.html', {'feedback_list': Feedback.objects.all().order_by('-id')})


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
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password updated successfully')
        return redirect('doc_secure')

    return render(request, 'doc_secure.html')


def user_home(request):
    profile = USER.objects.filter(user_id=request.user).first()
    context = {
        'profile': profile,
        'doctors': DOCTOR.objects.filter(Approval_Status='Approved'),
        'appointments': Appointment.objects.filter(user=profile).order_by('-id') if profile else [],
        'complaint_list': Complaint.objects.filter(user=profile).order_by('-id') if profile else [],
        'feedback_list': Feedback.objects.filter(user=profile).order_by('-id') if profile else [],
        'prescriptions': Prescription.objects.filter(patient=profile).order_by('-created_at') if profile else [],
    }
    return render(request, 'user_home.html', context)


def book_appointment(request):
    if request.method == "POST":
        profile = USER.objects.filter(user_id=request.user).first()
        doctor_user = User.objects.filter(pk=request.POST.get('doctor_id')).first()
        if profile and doctor_user:
            Appointment.objects.create(
                user=profile,
                DOCTOR_ID=doctor_user,
                date=request.POST.get('date', ''),
                time=request.POST.get('time', ''),
                status='Pending',
            )
            messages.success(request, 'Appointment requested')
    return redirect('user_home')


def search_med(request):
    query = request.GET.get('q', '')
    if query:
        medicines = MEDICINE.objects.filter(
            Q(Medicine_name__icontains=query) | Q(Generic_Name__icontains=query)
        ).prefetch_related('safety_notes').order_by('Medicine_name')
    else:
        medicines = MEDICINE.objects.none()
    return render(request, 'search_med.html', {'medicines': medicines, 'query': query})


def search_med_autocomplete(request):
    query = request.GET.get('q', '')
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


def submit_complaint(request):
    if request.method == "POST":
        profile = USER.objects.filter(user_id=request.user).first()
        if profile:
            Complaint.objects.create(
                user=profile,
                complaints=request.POST.get('complaint', ''),
                date=timezone.now().strftime('%Y-%m-%d'),
                reply='',
            )
            messages.success(request, 'Complaint submitted')
    return redirect('user_home')


def submit_feedback(request):
    if request.method == "POST":
        profile = USER.objects.filter(user_id=request.user).first()
        if profile:
            Feedback.objects.create(
                user=profile,
                feedback=request.POST.get('feedback', ''),
                date=timezone.now().strftime('%Y-%m-%d'),
            )
            messages.success(request, 'Feedback submitted')
    return redirect('user_home')


ALLOWED_PRESCRIPTION_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
}


def _validate_prescription_upload(uploaded_file):
    import os
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


@login_required
def prescription_upload(request):
    if request.method == "POST":
        profile = USER.objects.filter(user_id=request.user).first()
        if not profile:
            messages.error(request, 'Only patient accounts can upload prescriptions.')
            return redirect('home')

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

    return render(request, 'prescription_upload.html')


@login_required
def prescription_review(request, prescription_id):
    profile = USER.objects.filter(user_id=request.user).first()
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    if not profile or prescription.patient_id != profile.id:
        raise Http404

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


@login_required
def prescription_file_serve(request, file_id):
    profile = USER.objects.filter(user_id=request.user).first()
    prescription_file = get_object_or_404(PrescriptionFile, pk=file_id)
    if not profile or prescription_file.prescription.patient_id != profile.id:
        raise Http404
    return FileResponse(prescription_file.file.open('rb'), content_type=prescription_file.content_type)


@login_required
def prescription_delete(request, prescription_id):
    if request.method == "POST":
        profile = USER.objects.filter(user_id=request.user).first()
        prescription = get_object_or_404(Prescription, pk=prescription_id)
        if profile and prescription.patient_id == profile.id:
            prescription.delete()
            messages.success(request, 'Prescription deleted.')
        else:
            raise Http404
    return redirect('user_home')
