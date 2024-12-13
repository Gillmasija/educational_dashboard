from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class DashboardItem(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    ITEM_TYPES = [
        ('task', 'Task'),
        ('note', 'Note'),
        ('project', 'Project'),
        ('reminder', 'Reminder'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_items')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='task')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.item_type})"

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.due_date and self.status != 'completed':
            return self.due_date < timezone.now()
        return False

    @property
    def status_badge_color(self):
        status_colors = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'archived': 'secondary'
        }
        return status_colors.get(self.status, 'primary')

    @property
    def priority_badge_color(self):
        priority_colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger'
        }
        return priority_colors.get(self.priority, 'primary')

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set these values on creation
            from django.utils import timezone
            if not self.due_date:
                # Set default due date to 7 days from now if not specified
                self.due_date = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_classes')
    students = models.ManyToManyField(User, related_name='enrolled_classes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Classes'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Assignment(models.Model):
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    content = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.username}'s submission for {self.assignment.title}"
