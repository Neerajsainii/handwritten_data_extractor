from django.urls import path
from . import views

app_name = 'ocr_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('process/', views.process_image, name='process_image'),
] 