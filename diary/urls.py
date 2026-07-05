from django.urls import path

from . import views

app_name = 'diary'

urlpatterns = [
    path('', views.EntryListView.as_view(), name='list'),
    path('entry/new/', views.EntryCreateView.as_view(), name='create'),
    path('entry/<int:pk>/', views.EntryDetailView.as_view(), name='detail'),
    path('entry/<int:pk>/edit/', views.EntryUpdateView.as_view(), name='update'),
    path('entry/<int:pk>/delete/', views.EntryDeleteView.as_view(), name='delete'),
]
