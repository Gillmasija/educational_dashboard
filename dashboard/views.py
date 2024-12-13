from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import RegistrationForm, DashboardItemForm, ClassForm, AssignmentForm
from .models import DashboardItem, Class, Assignment, Submission

class RegistrationView(View):
    template_name = 'auth/register.html'

    def get(self, request):
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('dashboard:login')
        return render(request, self.template_name, {'form': form})

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Common data for both roles
        context['username'] = user.username
        context['dashboard_items'] = DashboardItem.objects.filter(owner=user)[:5]
        
        if hasattr(user, 'userprofile'):
            context['role'] = user.userprofile.role
        else:
            context['role'] = 'student'  # Default role
            
        if context['role'] == 'teacher':
            # Teacher-specific data
            context['classes'] = Class.objects.filter(teacher=user)
            context['total_students'] = User.objects.filter(
                enrolled_classes__teacher=user
            ).distinct().count()
            context['total_assignments'] = Assignment.objects.filter(
                class_obj__teacher=user
            ).count()
            context['recent_assignments'] = Assignment.objects.filter(
                class_obj__teacher=user
            ).order_by('-created_at')[:5]
            context['recent_submissions'] = Submission.objects.filter(
                assignment__class_obj__teacher=user
            ).order_by('-submitted_at')[:5]
        else:
            # Student-specific data
            context['enrolled_classes'] = Class.objects.filter(students=user)
            context['upcoming_assignments'] = Assignment.objects.filter(
                class_obj__students=user,
                due_date__gte=timezone.now()
            ).order_by('due_date')[:5]
            context['recent_grades'] = Submission.objects.filter(
                student=user
            ).exclude(grade=None).order_by('-submitted_at')[:5]
            # Add admin-created projects
            context['admin_projects'] = DashboardItem.objects.filter(
                owner__is_superuser=True
            ).order_by('-created_at')[:5]
            
        return context

class DashboardItemListView(LoginRequiredMixin, ListView):
    model = DashboardItem
    template_name = 'dashboard/item_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        return DashboardItem.objects.filter(owner=self.request.user)

class DashboardItemCreateView(LoginRequiredMixin, CreateView):
    model = DashboardItem
    form_class = DashboardItemForm
    template_name = 'dashboard/item_form.html'
    success_url = reverse_lazy('dashboard:item_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Item created successfully!')
        return super().form_valid(form)

class DashboardItemDetailView(LoginRequiredMixin, DetailView):
    model = DashboardItem
    template_name = 'dashboard/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return DashboardItem.objects.filter(owner=self.request.user)

class DashboardItemUpdateView(LoginRequiredMixin, UpdateView):
    model = DashboardItem
    form_class = DashboardItemForm
    template_name = 'dashboard/item_form.html'
    success_url = reverse_lazy('dashboard:item_list')

    def get_queryset(self):
        return DashboardItem.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Item updated successfully!')
        return super().form_valid(form)

class DashboardItemDeleteView(LoginRequiredMixin, DeleteView):
    model = DashboardItem
    template_name = 'dashboard/item_confirm_delete.html'
    success_url = reverse_lazy('dashboard:item_list')

    def get_queryset(self):
        return DashboardItem.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Item deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def dashboard(request):
    context = {
        'classes': Class.objects.filter(teacher=request.user)[:5],
        'assignments': Assignment.objects.filter(class_obj__teacher=request.user)[:5]
    }
    return render(request, 'dashboard/index.html', context)

# Class Views
class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'classes/list.html'
    context_object_name = 'classes'

    def get_queryset(self):
        return Class.objects.filter(teacher=self.request.user)

class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'classes/create.html'
    success_url = reverse_lazy('dashboard:class_list')

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        messages.success(self.request, 'Class created successfully!')
        return super().form_valid(form)

class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    form_class = ClassForm
    template_name = 'classes/edit.html'
    success_url = reverse_lazy('dashboard:class_list')

    def get_queryset(self):
        return Class.objects.filter(teacher=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Class updated successfully!')
        return super().form_valid(form)

class ClassDeleteView(LoginRequiredMixin, DeleteView):
    model = Class
    template_name = 'classes/delete.html'
    success_url = reverse_lazy('dashboard:class_list')

    def get_queryset(self):
        return Class.objects.filter(teacher=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Class deleted successfully!')
        return super().delete(request, *args, **kwargs)

class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'classes/detail.html'
    context_object_name = 'class'

    def get_queryset(self):
        return Class.objects.filter(teacher=self.request.user)

# Assignment Views
class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'assignments/list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        if self.request.user.has_perm('dashboard.view_assignment'):
            return Assignment.objects.filter(class_obj__teacher=self.request.user)
        return Assignment.objects.filter(class_obj__students=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context

class AssignmentCreateView(LoginRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/create.html'
    success_url = reverse_lazy('dashboard:assignment_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('dashboard.add_assignment'):
            messages.error(request, 'You do not have permission to create assignments.')
            return redirect('dashboard:assignment_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        messages.success(self.request, 'Assignment created successfully!')
        return super().form_valid(form)

class AssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/edit.html'
    success_url = reverse_lazy('dashboard:assignment_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('dashboard.change_assignment'):
            messages.error(request, 'You do not have permission to edit assignments.')
            return redirect('dashboard:assignment_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Assignment.objects.filter(teacher=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Assignment updated successfully!')
        return super().form_valid(form)

class AssignmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Assignment
    template_name = 'assignments/delete.html'
    success_url = reverse_lazy('dashboard:assignment_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('dashboard.delete_assignment'):
            messages.error(request, 'You do not have permission to delete assignments.')
            return redirect('dashboard:assignment_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Assignment.objects.filter(teacher=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Assignment deleted successfully!')
        return super().delete(request, *args, **kwargs)

class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = 'assignments/detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        return Assignment.objects.filter(class_obj__teacher=self.request.user)
class ClassStudentsView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'classes/students.html'
    context_object_name = 'class'

    def get_queryset(self):
        return Class.objects.filter(teacher=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrolled_students'] = self.object.students.all()
        context['available_students'] = User.objects.filter(groups__name='Student').exclude(
            id__in=self.object.students.values_list('id', flat=True)
        )
        return context
class AddStudentToClassView(LoginRequiredMixin, View):
    def post(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        student_id = request.POST.get('student_id')
        if student_id:
            student = get_object_or_404(User, pk=student_id)
            class_obj.students.add(student)
            messages.success(request, f'{student.username} has been added to {class_obj.name}')
        return redirect('dashboard:class_students', pk=pk)

class RemoveStudentFromClassView(LoginRequiredMixin, View):
    def post(self, request, pk):
        class_obj = get_object_or_404(Class, pk=pk, teacher=request.user)
        student_id = request.POST.get('student_id')
        if student_id:
            student = get_object_or_404(User, pk=student_id)
            class_obj.students.remove(student)
            messages.success(request, f'{student.username} has been removed from {class_obj.name}')
        return redirect('dashboard:class_students', pk=pk)