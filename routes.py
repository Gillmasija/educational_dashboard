from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
import logging
from database import db
from datetime import datetime
from models import (User, UserProfile, Class, ClassStudents, Assignment, 
                   Submission, Grade, Attendance, Notification)
from forms import (LoginForm, RegistrationForm, ProfileForm, ClassForm,
                  AssignmentForm, SubmissionForm, GradeForm, AttendanceForm)
from werkzeug.utils import secure_filename
import os
import logging

logger = logging.getLogger(__name__)

# Blueprint definitions
auth_bp = Blueprint('auth', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
assignment_bp = Blueprint('assignment', __name__)
class_bp = Blueprint('class', __name__)

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        flash('Invalid email or password', 'error')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if username or email already exists
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('auth/register.html', form=form)
            
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('auth/register.html', form=form)
            
            user = User(username=form.username.data,
                       email=form.email.data,
                       role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Create user profile
            profile = UserProfile(user=user)
            db.session.add(profile)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during registration: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Dashboard routes
@dashboard_bp.route('/')
@login_required
def index():
    try:
        if current_user.role == 'teacher':
            classes = Class.query.filter_by(teacher_id=current_user.id).all()
            assignments = Assignment.query.join(Class).filter(
                Class.teacher_id == current_user.id
            ).order_by(Assignment.due_date.desc()).all()
            logger.info(f"Teacher dashboard loaded for user {current_user.id}")
        else:
            assignments = Assignment.query.join(Class).join(ClassStudents).filter(
                ClassStudents.student_id == current_user.id
            ).order_by(Assignment.due_date.desc()).all()
            classes = Class.query.join(ClassStudents).filter(
                ClassStudents.student_id == current_user.id
            ).all()
            logger.info(f"Student dashboard loaded for user {current_user.id}")
        
        return render_template('dashboard/index.html',
                             classes=classes if 'classes' in locals() else [],
                             assignments=assignments,
                             now=datetime.utcnow())
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'error')
        return render_template('dashboard/index.html', 
                             classes=[],
                             assignments=[],
                             now=datetime.utcnow())

@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if not current_user.profile:
            profile = UserProfile(user=current_user, bio=form.bio.data)
            db.session.add(profile)
        else:
            current_user.profile.bio = form.bio.data
        db.session.commit()
        flash('Profile updated successfully')

    context = {'form': form}
    
    if current_user.role == 'teacher':
        # Get teacher statistics
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        total_students = db.session.query(ClassStudents.student_id).distinct().join(
            Class, Class.id == ClassStudents.class_id
        ).filter(Class.teacher_id == current_user.id).count()
        total_assignments = Assignment.query.join(Class).filter(
            Class.teacher_id == current_user.id
        ).count()
        
        context.update({
            'classes': classes,
            'total_students': total_students,
            'total_assignments': total_assignments
        })
    else:
        # Get student statistics
        total_assignments = Assignment.query.join(Class).join(ClassStudents).filter(
            ClassStudents.student_id == current_user.id
        ).count()
        completed_assignments = Submission.query.filter_by(
            student_id=current_user.id
        ).count()
        grades = Grade.query.join(Submission).filter(
            Submission.student_id == current_user.id
        ).all()
        average_grade = sum(grade.score for grade in grades) / len(grades) if grades else None
        attendance_records = Attendance.query.filter_by(
            student_id=current_user.id
        ).all()
        attendance_rate = (
            sum(1 for a in attendance_records if a.status == 'present') / len(attendance_records) * 100
            if attendance_records else None
        )
        
        context.update({
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'average_grade': f"{average_grade:.1f}" if average_grade is not None else 'N/A',
            'attendance_rate': f"{attendance_rate:.1f}" if attendance_rate is not None else 'N/A'
        })

    return render_template('dashboard/profile.html', **context)

# Assignment routes
@assignment_bp.route('/assignments')
@login_required
def list():
    try:
        if current_user.role == 'teacher':
            assignments = Assignment.query.join(Class).filter(Class.teacher_id == current_user.id).all()
            logger.info(f"Retrieved {len(assignments)} assignments for teacher {current_user.id}")
        else:
            assignments = Assignment.query.join(Class).join(ClassStudents).filter(
                ClassStudents.student_id == current_user.id
            ).order_by(Assignment.due_date.desc()).all()
            logger.info(f"Retrieved {len(assignments)} assignments for student {current_user.id}")
        return render_template('assignments/list.html', assignments=assignments, now=datetime.utcnow())
    except Exception as e:
        logger.error(f"Error retrieving assignments: {str(e)}")
        flash('An error occurred while loading assignments', 'error')
        return render_template('assignments/list.html', assignments=[])

@assignment_bp.route('/assignments/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'teacher':
        flash('Only teachers can create assignments')
        return redirect(url_for('assignment.list'))
        
    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            teacher_id=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment created')
        return redirect(url_for('assignment.list'))
    return render_template('assignments/create.html', form=form)

# Class routes
@class_bp.route('/classes')
@login_required
def list():
    if current_user.role == 'teacher':
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
    else:
        classes = Class.query.join(ClassStudents).filter_by(
            student_id=current_user.id).all()
    return render_template('classes/list.html', classes=classes)

@class_bp.route('/classes/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'teacher':
        flash('Only teachers can create classes')
        return redirect(url_for('class.list'))
        
    form = ClassForm()
    if form.validate_on_submit():
        class_obj = Class(
            name=form.name.data,
            description=form.description.data,
            teacher_id=current_user.id
        )
        db.session.add(class_obj)
        db.session.commit()
        flash('Class created')
        return redirect(url_for('class.list'))
    return render_template('classes/create.html', form=form)