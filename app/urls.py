"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from .import views


urlpatterns = [
path('',views.home,name='home'),

path('login',views.login,name='login'),
path('logout',views.logout_view,name='logout'),

path('registration',views.registration,name='registration'),
path('doc_reg/',views.doc_reg,name='doc_reg'),

path('adminindex/',views.adminindex,name='adminindex'),

path('add_med/',views.add_med,name='add_med'),

path('complaints',views.complaints,name='complaints'),

path('manage_doctor/',views.manage_doctor,name='manage_doctor'),

path('feedback',views.feedback,name='feedback'),

path('appoint_manage',views.appoint_manage,name='appoint_manage'),

path('view_user/',views.view_user,name='view_user'),

path('doctor_home/',views.doctor_home,name='doctor_home'),

path('doc_med/',views.doc_med,name='doc_med'),
path('schedule/',views.schedule,name='schedule'),
path('doc_complaint/',views.doc_complaint,name='doc_complaint'),
path('doc_feedback/',views.doc_feedback,name='doc_feedback'),
path('doc_secure/',views.doc_secure,name='doc_secure'),

path('user_home/',views.user_home,name='user_home'),
path('book_appointment/',views.book_appointment,name='book_appointment'),
path('search_med/',views.search_med,name='search_med'),
path('search_med/autocomplete/',views.search_med_autocomplete,name='search_med_autocomplete'),
path('submit_complaint/',views.submit_complaint,name='submit_complaint'),
path('submit_feedback/',views.submit_feedback,name='submit_feedback'),

]
