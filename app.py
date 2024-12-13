import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_key_123')
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', 'csrf_secret_key_123')
app.config['WTF_CSRF_ENABLED'] = True

csrf = CSRFProtect()
csrf.init_app(app)

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            host=os.environ.get('PGHOST'),
            port=os.environ.get('PGPORT')
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                role VARCHAR(20) NOT NULL
            )
        ''')
        
        # Create classes table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                teacher_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create class_students table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS class_students (
                id SERIAL PRIMARY KEY,
                class_id INTEGER REFERENCES classes(id),
                student_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(class_id, student_id)
            )
        ''')

        # Create schedules table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                class_id INTEGER REFERENCES classes(id),
                day_of_week VARCHAR(10) NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create assignments table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                class_id INTEGER REFERENCES classes(id),
                title VARCHAR(200) NOT NULL,
                description TEXT,
                due_date TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create student_assignments table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS student_assignments (
                id SERIAL PRIMARY KEY,
                assignment_id INTEGER REFERENCES assignments(id),
                student_id INTEGER REFERENCES users(id),
                submission_text TEXT,
                submitted_at TIMESTAMP,
                grade NUMERIC,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(assignment_id, student_id)
            )
        ''')
        
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Initialize empty lists
        classes = []
        assignments = []
        schedules = []
        completed_assignments = 0
        
        # Get classes based on role
        if session['role'] == 'teacher':
            cur.execute("""
                SELECT * FROM classes WHERE teacher_id = %s
                ORDER BY created_at DESC
            """, (session['user_id'],))
            classes = cur.fetchall() or []
            
            if classes:
                # Get assignments for teacher's classes
                cur.execute("""
                    SELECT a.*, c.name as class_name
                    FROM assignments a
                    JOIN classes c ON a.class_id = c.id
                    WHERE c.teacher_id = %s
                    ORDER BY a.due_date ASC
                    LIMIT 5
                """, (session['user_id'],))
                assignments = cur.fetchall() or []
        else:
            # Get student's classes
            cur.execute("""
                SELECT c.* FROM classes c
                JOIN class_students cs ON c.id = cs.class_id
                WHERE cs.student_id = %s
                ORDER BY c.created_at DESC
            """, (session['user_id'],))
            classes = cur.fetchall() or []
            
            if classes:
                # Get assignments for student's classes
                cur.execute("""
                    SELECT a.*, c.name as class_name
                    FROM assignments a
                    JOIN classes c ON a.class_id = c.id
                    JOIN class_students cs ON c.id = cs.class_id
                    WHERE cs.student_id = %s
                    ORDER BY a.due_date ASC
                    LIMIT 5
                """, (session['user_id'],))
                assignments = cur.fetchall() or []
        
        # Get schedules if there are classes
        if classes:
            class_ids = [c['id'] for c in classes]
            placeholders = ','.join(['%s'] * len(class_ids))
            cur.execute(f"""
                SELECT s.*, c.name as class_name
                FROM schedules s
                JOIN classes c ON s.class_id = c.id
                WHERE s.class_id IN ({placeholders})
                ORDER BY s.day_of_week, s.start_time
            """, tuple(class_ids))
            schedules = cur.fetchall() or []
            
        logger.info(f"Retrieved data for user {session['user_id']}: "
                   f"{len(classes)} classes, {len(assignments)} assignments, "
                   f"{len(schedules)} schedules")
            
        return render_template('dashboard/index.html', 
                             classes=classes,
                             assignments=assignments,
                             schedules=schedules,
                             now=datetime.now())
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('An error occurred while loading the dashboard', 'error')
        return render_template('dashboard/index.html', 
                             classes=[],
                             assignments=[],
                             schedules=[],
                             now=datetime.now())
    finally:
        cur.close()
        conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    from forms import LoginForm
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
            
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash('Welcome back!', 'success')
                return redirect(url_for('index'))
                
            flash('Invalid email or password', 'error')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')
        finally:
            cur.close()
            conn.close()
            
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, (username, email, generate_password_hash(password), role))
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            flash('Username or email already exists.', 'error')
        finally:
            cur.close()
            conn.close()
            
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Class management routes
@app.route('/classes')
def list_classes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if session['role'] == 'teacher':
            cur.execute("""
                SELECT c.*, COUNT(cs.student_id) as student_count 
                FROM classes c 
                LEFT JOIN class_students cs ON c.id = cs.class_id 
                WHERE c.teacher_id = %s 
                GROUP BY c.id 
                ORDER BY c.created_at DESC
            """, (session['user_id'],))
        else:
            cur.execute("""
                SELECT c.*, u.username as teacher_name 
                FROM classes c
                JOIN users u ON c.teacher_id = u.id
                JOIN class_students cs ON c.id = cs.class_id
                WHERE cs.student_id = %s
                ORDER BY c.created_at DESC
            """, (session['user_id'],))
            
        classes = cur.fetchall()
        return render_template('classes/list.html', 
                             classes=classes, 
                             is_teacher=(session['role'] == 'teacher'))
    finally:
        cur.close()
        conn.close()

@app.route('/classes/create', methods=['GET', 'POST'])
def create_class():
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Only teachers can create classes', 'error')
        return redirect(url_for('list_classes'))
    
    if request.method == 'POST':
        logger.info("Received POST request to create class")
        name = request.form.get('name')
        description = request.form.get('description')
        
        logger.debug(f"Form data received - Name: {name}, Description: {description}")
        
        if not name:
            logger.warning("Class name not provided")
            flash('Class name is required', 'error')
            return render_template('classes/create.html')
        
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Create the class
            logger.info(f"Attempting to create class '{name}' for teacher {session['user_id']}")
            cur.execute("""
                INSERT INTO classes (name, description, teacher_id)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, description, session['user_id']))
            
            class_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Successfully created class with ID {class_id} for teacher {session['user_id']}")
            flash('Class created successfully', 'success')
            return redirect(url_for('list_classes'))
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error creating class: {str(e)}")
            flash('Error creating class. Please try again.', 'error')
            return render_template('classes/create.html')
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error creating class: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return render_template('classes/create.html')
        finally:
            if conn:
                conn.close()
    
    return render_template('classes/create.html')

@app.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
def edit_class(class_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Only teachers can edit classes', 'error')
        return redirect(url_for('list_classes'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM classes 
            WHERE id = %s AND teacher_id = %s
        """, (class_id, session['user_id']))
        
        class_obj = cur.fetchone()
        if not class_obj:
            flash('Class not found', 'error')
            return redirect(url_for('list_classes'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash('Class name is required', 'error')
                return render_template('classes/edit.html', class_obj=class_obj)
            
            cur.execute("""
                UPDATE classes 
                SET name = %s, description = %s
                WHERE id = %s AND teacher_id = %s
            """, (name, description, class_id, session['user_id']))
            
            conn.commit()
            flash('Class updated successfully', 'success')
            return redirect(url_for('list_classes'))
        
        return render_template('classes/edit.html', class_obj=class_obj)
    finally:
        cur.close()
        conn.close()

@app.route('/classes/<int:class_id>/students', methods=['GET', 'POST'])
def manage_students(class_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Only teachers can manage students', 'error')
        return redirect(url_for('list_classes'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get class details
        cur.execute("""
            SELECT * FROM classes 
            WHERE id = %s AND teacher_id = %s
        """, (class_id, session['user_id']))
        
        class_obj = cur.fetchone()
        if not class_obj:
            flash('Class not found', 'error')
            return redirect(url_for('list_classes'))
        
        if request.method == 'POST':
            student_email = request.form.get('student_email')
            
            # Find student by email
            cur.execute("SELECT id FROM users WHERE email = %s AND role = 'student'", 
                       (student_email,))
            student = cur.fetchone()
            
            if not student:
                flash('Student not found', 'error')
            else:
                try:
                    cur.execute("""
                        INSERT INTO class_students (class_id, student_id)
                        VALUES (%s, %s)
                    """, (class_id, student['id']))
                    conn.commit()
                    flash('Student added to class', 'success')
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    flash('Student is already in this class', 'error')
        
        # Get enrolled students
        cur.execute("""
            SELECT u.username, u.email, cs.created_at as enrolled_at
            FROM users u
            JOIN class_students cs ON u.id = cs.student_id
            WHERE cs.class_id = %s
            ORDER BY u.username
        """, (class_id,))
        students = cur.fetchall()
        
        return render_template('classes/students.html', 
                             class_obj=class_obj,
                             students=students)
    finally:
        cur.close()
        conn.close()

# Schedule management routes
@app.route('/classes/<int:class_id>/schedule', methods=['GET', 'POST'])
def manage_schedule(class_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Only teachers can manage schedules', 'error')
        return redirect(url_for('index'))
    
    from forms import ScheduleForm
    form = ScheduleForm()
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get class details
        cur.execute("""
            SELECT * FROM classes 
            WHERE id = %s AND teacher_id = %s
        """, (class_id, session['user_id']))
        class_obj = cur.fetchone()
        
        if not class_obj:
            flash('Class not found', 'error')
            return redirect(url_for('index'))
        
        if form.validate_on_submit():
            try:
                # Validate time format
                cur.execute("""
                    INSERT INTO schedules (class_id, day_of_week, start_time, end_time)
                    VALUES (%s, %s, %s::time, %s::time)
                """, (class_id, form.day.data, form.start_time.data, form.end_time.data))
                conn.commit()
                flash('Schedule added successfully', 'success')
                return redirect(url_for('manage_schedule', class_id=class_id))
            except psycopg2.Error as e:
                logger.error(f"Database error adding schedule: {str(e)}")
                flash('Error adding schedule. Please check the time format.', 'error')
                conn.rollback()
            except Exception as e:
                logger.error(f"Unexpected error adding schedule: {str(e)}")
                flash('An unexpected error occurred. Please try again.', 'error')
                conn.rollback()
            
        # Get existing schedules
        cur.execute("""
            SELECT 
                id,
                day_of_week,
                TO_CHAR(start_time, 'HH24:MI') as start_time,
                TO_CHAR(end_time, 'HH24:MI') as end_time
            FROM schedules 
            WHERE class_id = %s 
            ORDER BY CASE 
                WHEN day_of_week = 'Monday' THEN 1
                WHEN day_of_week = 'Tuesday' THEN 2
                WHEN day_of_week = 'Wednesday' THEN 3
                WHEN day_of_week = 'Thursday' THEN 4
                WHEN day_of_week = 'Friday' THEN 5
                ELSE 6
            END, start_time
        """, (class_id,))
        schedules = cur.fetchall()
        
        return render_template('classes/schedule.html', 
                             class_obj=class_obj, 
                             schedules=schedules,
                             form=form)
    finally:
        cur.close()
        conn.close()

# Assignment management routes
@app.route('/classes/<int:class_id>/assignments', methods=['GET', 'POST'])
def manage_assignments(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get class details
        cur.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
        class_obj = cur.fetchone()
        
        if not class_obj:
            flash('Class not found', 'error')
            return redirect(url_for('index'))
        
        # Check if user is teacher or enrolled student
        if session['role'] != 'teacher' and class_obj['teacher_id'] != session['user_id']:
            cur.execute("""
                SELECT 1 FROM class_students 
                WHERE class_id = %s AND student_id = %s
            """, (class_id, session['user_id']))
            if not cur.fetchone():
                flash('Access denied', 'error')
                return redirect(url_for('index'))
        
        if request.method == 'POST' and session['role'] == 'teacher':
            title = request.form['title']
            description = request.form['description']
            due_date = request.form['due_date']
            
            cur.execute("""
                INSERT INTO assignments (class_id, title, description, due_date)
                VALUES (%s, %s, %s, %s)
            """, (class_id, title, description, due_date))
            
            flash('Assignment created successfully', 'success')
        
        # Get assignments
        cur.execute("""
            SELECT a.*, 
                   CASE WHEN sa.submitted_at IS NOT NULL 
                        THEN true ELSE false END as submitted,
                   sa.grade
            FROM assignments a
            LEFT JOIN student_assignments sa ON 
                a.id = sa.assignment_id AND sa.student_id = %s
            WHERE a.class_id = %s
            ORDER BY a.due_date DESC
        """, (session['user_id'], class_id))
        assignments = cur.fetchall()
        
        return render_template('classes/assignments.html',
                             class_obj=class_obj,
                             assignments=assignments,
                             is_teacher=(session['role'] == 'teacher'))
    finally:
        cur.close()
        conn.close()

@app.route('/assignments/<int:assignment_id>/submit', methods=['GET', 'POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Only students can submit assignments', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get assignment details
        cur.execute("""
            SELECT a.*, c.name as class_name 
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.id = %s
        """, (assignment_id,))
        assignment = cur.fetchone()
        
        if not assignment:
            flash('Assignment not found', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            submission_text = request.form['submission_text']
            
            cur.execute("""
                INSERT INTO student_assignments 
                (assignment_id, student_id, submission_text, submitted_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (assignment_id, student_id) DO UPDATE
                SET submission_text = EXCLUDED.submission_text,
                    submitted_at = CURRENT_TIMESTAMP
            """, (assignment_id, session['user_id'], submission_text))
            
            flash('Assignment submitted successfully', 'success')
            return redirect(url_for('manage_assignments', 
                                  class_id=assignment['class_id']))
        
        # Check if already submitted
        cur.execute("""
            SELECT * FROM student_assignments
            WHERE assignment_id = %s AND student_id = %s
        """, (assignment_id, session['user_id']))
        submission = cur.fetchone()
        
        return render_template('assignments/submit.html',
                             assignment=assignment,
                             submission=submission)
    finally:
        cur.close()
        conn.close()

    # Dashboard data retrieval functions
    def get_upcoming_sessions(user_id):
        """Get upcoming class sessions for a teacher."""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT 
                    cs.start_time,
                    cs.end_time,
                    c.name as class_name,
                    COUNT(ce.student_id) as student_count,
                    CASE
                        WHEN cs.start_time <= CURRENT_TIMESTAMP + INTERVAL '15 minutes' 
                        THEN 'success'
                        ELSE 'secondary'
                    END as status_color
                FROM class_schedules cs
                JOIN classes c ON cs.class_id = c.id
                LEFT JOIN class_enrollments ce ON c.id = ce.class_id
                WHERE c.teacher_id = %s
                AND cs.start_time >= CURRENT_DATE
                GROUP BY cs.id, cs.start_time, cs.end_time, c.name
                ORDER BY cs.start_time ASC
                LIMIT 5
            """, (user_id,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        try:
            user_id = session['user_id']
            upcoming_sessions = get_upcoming_sessions(user_id)
            recent_activities = get_recent_activity(user_id)
            
            return render_template('dashboard/index.html',
                                 upcoming_sessions=upcoming_sessions,
                                 recent_activities=recent_activities,
                                 now=datetime.now())
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            flash("An error occurred while loading the dashboard.", "error")
            return redirect(url_for('login'))
# Dashboard Card CRUD Routes
@app.route('/api/cards/<int:card_id>', methods=['PUT', 'DELETE'])
def manage_card(card_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if request.method == 'PUT':
            data = request.get_json()
            title = data.get('title')
            content = data.get('content')
            
            if not title:
                return jsonify({'success': False, 'error': 'Title is required'}), 400
            
            cur.execute("""
                UPDATE dashboard_cards 
                SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
            """, (title, content, card_id))
            
            updated = cur.fetchone()
            if updated:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Card not found'}), 404
            
        elif request.method == 'DELETE':
            cur.execute("DELETE FROM dashboard_cards WHERE id = %s RETURNING id", (card_id,))
            deleted = cur.fetchone()
            
            if deleted:
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Card not found'}), 404
    
    except Exception as e:
        logger.error(f"Error managing card {card_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/cards', methods=['POST'])
def create_card():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        card_type = data.get('card_type', 'default')
        position = data.get('position', 0)
        
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        cur.execute("""
            INSERT INTO dashboard_cards (title, content, card_type, position)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (title, content, card_type, position))
        
        new_card = cur.fetchone()
        return jsonify({'success': True, 'id': new_card['id']})
    
    except Exception as e:
        logger.error(f"Error creating card: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500
    finally:
        cur.close()
        conn.close()
if __name__ == '__main__':
    try:
        init_db()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise