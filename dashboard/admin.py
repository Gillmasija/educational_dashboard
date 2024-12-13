from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Class, Assignment, Submission, DashboardItem

@admin.register(DashboardItem)
class DashboardItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'item_type', 'status', 'priority', 'due_date', 'is_overdue', 'created_at')
    list_filter = ('status', 'priority', 'item_type', 'created_at')
    search_fields = ('title', 'description', 'owner__username', 'owner__email')
    date_hierarchy = 'created_at'
    list_editable = ('status', 'priority')
    readonly_fields = ('created_at', 'updated_at', 'is_overdue')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'owner')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'item_type'),
            'description': 'Set the current status and priority level of the item'
        }),
        ('Dates', {
            'fields': ('due_date', 'created_at', 'updated_at'),
            'description': 'Important dates for this item'
        }),
    )
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner')

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_obj', 'due_date', 'status', 'created_at')
    list_filter = ('status', 'due_date', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'due_date'

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at', 'grade')
    list_filter = ('submitted_at', 'grade')
    search_fields = ('student__username', 'assignment__title', 'feedback')
    date_hierarchy = 'submitted_at'

# Re-register UserAdmin with minimal customization
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
