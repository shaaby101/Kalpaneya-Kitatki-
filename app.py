import sqlite3
from flask import Flask, render_template, g, jsonify, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
import datetime

# --- App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_for_local_use_only' # Change this
DATABASE = 'kannada_letterboxd.db' # Renamed DB for clarity

# --- Utility Setup ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Page to redirect to if user is not logged in
login_manager.login_message_category = 'info'

# --- Database Setup ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        print("Initialized the database.")
        populate_db() # Populate with our author/work data

def populate_db():
    db = get_db()
    
    # --- Kuvempu (Data from our sources) ---
    db.execute('INSERT INTO Author (name_kannada, name_english, biography, era) VALUES (?, ?, ?, ?)',
               ('ಕುವೆಂಪು', 'Kuvempu', 'Kuppali Venkatappa Puttappa...', 'Navodaya'))
    kuvempu_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
               (kuvempu_id, 'ಕಾನೂರು ಹೆಗ್ಗಡಿತಿ', 'Kanooru Heggadithi', 'Novel', 'A novel about feudal life in Malnad.'))
    db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
               (kuvempu_id, 'ಶ್ರೀ ರಾಮಾಯಣ ದರ್ಶನಂ', 'Sri Ramayana Darshanam', 'Epic Poetry', 'A modern retelling of the Ramayana.'))
    
    # --- Poornachandra Tejaswi (Data from our sources) ---
    db.execute('INSERT INTO Author (name_kannada, name_english, biography, era) VALUES (?, ?, ?, ?)',
               ('ಪೂರ್ಣಚಂದ್ರ ತೇಜಸ್ವಿ', 'Poornachandra Tejaswi', 'K. P. Poornachandra Tejaswi was a prominent writer...', 'Navya/Post-Modern'))
    tejaswi_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
               (tejaswi_id, 'ಕರ್ವಾಲೊ', 'Carvalho', 'Novel', 'A novel about an amateur scientist.'))
    db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
               (tejaswi_id, 'ಚಿದಂಬರ ರಹಸ್ಯ', 'Chidambara Rahasya', 'Novel', 'A mystery novel set in a rural backdrop.'))

    db.commit()
    print("Populated the database with authors and works.")

@app.cli.command('init')
def init_db_command():
    """Command to initialize the database: `flask init`"""
    init_db()
    print('Database initialization complete.')

# --- User & Login Management ---
class User(UserMixin):
    """User class for Flask-Login."""
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute('SELECT * FROM User WHERE user_id = ?', (user_id,)).fetchone()
    if user_data:
        return User(user_data['user_id'], user_data['username'], user_data['email'])
    return None

# --- Forms (Using Flask-WTF) ---
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        db = get_db()
        user = db.execute('SELECT * FROM User WHERE username = ?', (username.data,)).fetchone()
        if user:
            raise ValidationError('Username is already taken.')

    def validate_email(self, email):
        db = get_db()
        user = db.execute('SELECT * FROM User WHERE email = ?', (email.data,)).fetchone()
        if user:
            raise ValidationError('Email is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ReviewForm(FlaskForm):
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    review_text = TextAreaField('Review (Optional)', validators=[Length(max=5000)])
    date_read = DateField('Date Read', format='%Y-%m-%d', default=datetime.date.today, validators=[DataRequired()])
    submit = SubmitField('Log Book')

# --- Public Routes (Auth) ---

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db = get_db()
        try:
            db.execute('INSERT INTO User (username, email, password_hash) VALUES (?, ?, ?)',
                       (form.username.data, form.email.data, hashed_password))
            db.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('Username or Email already exists.', 'danger')
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        user_data = db.execute('SELECT * FROM User WHERE email = ?', (form.email.data,)).fetchone()
        if user_data and bcrypt.check_password_hash(user_data['password_hash'], form.password.data):
            user = User(user_data['user_id'], user_data['username'], user_data['email'])
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('homepage'))

# --- Main App Routes ---

@app.route('/')
def homepage():
    """Homepage now shows all WORKS, which is more visual (Letterboxd-style)."""
    db = get_db()
    works = db.execute('''
        SELECT Work.*, Author.name_kannada as author_kannada, Author.name_english as author_english
        FROM Work
        JOIN Author ON Work.author_id = Author.author_id
    ''').fetchall()
    return render_template('index.html', works=works)

@app.route('/work/<int:work_id>', methods=['GET', 'POST'])
def work_details(work_id):
    """Shows details for a single work, its reviews, and the review form."""
    db = get_db()
    work = db.execute('''
        SELECT Work.*, Author.name_kannada as author_kannada, Author.name_english as author_english
        FROM Work
        JOIN Author ON Work.author_id = Author.author_id
        WHERE Work.work_id = ?
    ''', (work_id,)).fetchone()

    if work is None:
        abort(404)

    reviews = db.execute('''
        SELECT Review.*, User.username
        FROM Review
        JOIN User ON Review.user_id = User.user_id
        WHERE Review.work_id = ?
        ORDER BY Review.date_logged DESC
    ''', (work_id,)).fetchall()
    
    # --- Review Form Logic ---
    form = ReviewForm()
    if form.validate_on_submit() and current_user.is_authenticated:
        try:
            db.execute('''
                INSERT INTO Review (user_id, work_id, rating, review_text, date_read)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, work_id, form.rating.data, form.review_text.data, form.date_read.data))
            db.commit()
            flash('Your review has been logged!', 'success')
            return redirect(url_for('work_details', work_id=work_id))
        except Exception as e:
            db.rollback()
            flash(f'Error logging review: {e}', 'danger')
    
    # Pre-fill form if user is logged in
    elif request.method == 'GET' and current_user.is_authenticated:
        form.date_read.data = datetime.date.today()
        
    return render_template('work_details.html', work=work, reviews=reviews, form=form)

@app.route('/profile/<string:username>')
def user_profile(username):
    """Shows a user's profile and all their reviews."""
    db = get_db()
    user = db.execute('SELECT * FROM User WHERE username = ?', (username,)).fetchone()
    
    if user is None:
        abort(404)
        
    reviews = db.execute('''
        SELECT Review.*, Work.title_kannada, Work.title_english
        FROM Review
        JOIN Work ON Review.work_id = Work.work_id
        WHERE Review.user_id = ?
        ORDER BY Review.date_read DESC
    ''', (user['user_id'],)).fetchall()
    
    return render_template('profile.html', user=user, reviews=reviews)

# --- Auto-complete search (we can reuse this, but make it better) ---
@app.route('/search-autocomplete')
def search_autocomplete():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    db = get_db()
    authors = db.execute('SELECT author_id, name_kannada, name_english FROM Author WHERE name_kannada LIKE ? OR name_english LIKE ?', (f'%{query}%', f'%{query}%')).fetchall()
    works = db.execute('SELECT work_id, title_kannada, title_english FROM Work WHERE title_kannada LIKE ? OR title_english LIKE ?', (f'%{query}%', f'%{query}%')).fetchall()

    suggestions = []
    for author in authors:
        suggestions.append({'label': f"{author['name_english']} ({author['name_kannada']})", 'type': 'Author', 'url': f'/author/{author["author_id"]}'}) # We need to build this page
    for work in works:
        suggestions.append({'label': f"{work['title_english']} ({work['title_kannada']})", 'type': 'Work', 'url': f'/work/{work["work_id"]}'})
        
    return jsonify(suggestions)


if __name__ == '__main__':
    app.run(debug=True)