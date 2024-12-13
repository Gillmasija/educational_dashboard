from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='dashboard:login', template_name='auth/login.html'), name='logout'),
    path('register/', views.RegistrationView.as_view(), name='register'),
    
    # Dashboard URLs
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('items/', views.DashboardItemListView.as_view(), name='item_list'),
    path('items/create/', views.DashboardItemCreateView.as_view(), name='item_create'),
    path('items/<int:pk>/', views.DashboardItemDetailView.as_view(), name='item_detail'),
    path('items/<int:pk>/edit/', views.DashboardItemUpdateView.as_view(), name='item_edit'),
    path('items/<int:pk>/delete/', views.DashboardItemDeleteView.as_view(), name='item_delete'),
    
    # Class URLs
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/create/', views.ClassCreateView.as_view(), name='class_create'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/<int:pk>/edit/', views.ClassUpdateView.as_view(), name='class_edit'),
    path('classes/<int:pk>/delete/', views.ClassDeleteView.as_view(), name='class_delete'),
    path('classes/<int:pk>/students/', views.ClassStudentsView.as_view(), name='class_students'),
    path('classes/<int:pk>/students/add/', views.AddStudentToClassView.as_view(), name='add_student_to_class'),
    path('classes/<int:pk>/students/remove/', views.RemoveStudentFromClassView.as_view(), name='remove_student_from_class'),
    
    # Assignment URLs
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/<int:pk>/edit/', views.AssignmentUpdateView.as_view(), name='assignment_edit'),
    path('assignments/<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
]