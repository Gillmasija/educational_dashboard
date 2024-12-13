from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, PasswordField, 
                    EmailField, DateTimeField, FileField)
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher')
    ], validators=[DataRequired()])

class ProfileForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[Length(max=500)])

class ClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')

class AssignmentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    due_date = StringField('Due Date', validators=[DataRequired()])
    file = FileField('Assignment File')

class SubmissionForm(FlaskForm):
    file = FileField('Submission File', validators=[DataRequired()])

class GradeForm(FlaskForm):
    score = StringField('Score', validators=[DataRequired()])
    feedback = TextAreaField('Feedback')

class AttendanceForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ])
    note = TextAreaField('Note')

class ScheduleForm(FlaskForm):
    day = SelectField('Day', choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday')
    ], validators=[DataRequired()])
    start_time = StringField('Start Time', validators=[DataRequired()])
    end_time = StringField('End Time', validators=[DataRequired()])
