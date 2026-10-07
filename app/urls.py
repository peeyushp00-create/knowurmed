from django.urls import path

from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('login', views.login, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('registration', views.registration, name='registration'),
    path('doc_reg/', views.doc_reg, name='doc_reg'),
    path('search_med/', views.search_med, name='search_med'),
    path('search_med/autocomplete/', views.search_med_autocomplete, name='search_med_autocomplete'),

    # Admin
    path('adminindex/', views.adminindex, name='adminindex'),
    path('add_med/', views.add_med, name='add_med'),
    path('manage_doctor/', views.manage_doctor, name='manage_doctor'),
    path('view_user/', views.view_user, name='view_user'),
    path('complaints', views.complaints, name='complaints'),
    path('feedback', views.feedback, name='feedback'),

    # Admin and doctor
    path('appoint_manage', views.appoint_manage, name='appoint_manage'),

    # Doctor
    path('doctor_home/', views.doctor_home, name='doctor_home'),
    path('doc_med/', views.doc_med, name='doc_med'),
    path('schedule/', views.schedule, name='schedule'),
    path('doc_complaint/', views.doc_complaint, name='doc_complaint'),
    path('doc_feedback/', views.doc_feedback, name='doc_feedback'),
    path('doc_secure/', views.doc_secure, name='doc_secure'),

    # Patient
    path('user_home/', views.user_home, name='user_home'),
    path('book_appointment/', views.book_appointment, name='book_appointment'),
    path('submit_complaint/', views.submit_complaint, name='submit_complaint'),
    path('submit_feedback/', views.submit_feedback, name='submit_feedback'),
    path('prescription/upload/', views.prescription_upload, name='prescription_upload'),
    path('prescription/<int:prescription_id>/review/', views.prescription_review, name='prescription_review'),
    path('prescription/<int:prescription_id>/delete/', views.prescription_delete, name='prescription_delete'),
    path('prescription/file/<int:file_id>/', views.prescription_file_serve, name='prescription_file_serve'),
]
