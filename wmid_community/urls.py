from django.urls import path, include

urlpatterns = [
    path('', include('directory.urls')),
]
