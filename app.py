import sqlite3
import json
import os
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

def get_or_create_author(db, name_kannada, name_english, biography, era, image_url):
    """Checks if author exists. If not, inserts and returns ID. Prevents duplicates."""
    existing = db.execute('SELECT author_id FROM Author WHERE name_english = ?', (name_english,)).fetchone()
    if existing:
        return existing['author_id']
    
    db.execute('INSERT INTO Author (name_kannada, name_english, biography, era, image_url) VALUES (?, ?, ?, ?, ?)',
               (name_kannada, name_english, biography, era, image_url))
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]

def populate_db():
    db = get_db()
    
    # Load data from JSON files
    writers_data = []
    poets_data = []
    
    # Load writers JSON
    writers_path = os.path.join(os.path.dirname(__file__), 'databases', 'writer.json')
    if os.path.exists(writers_path):
        with open(writers_path, 'r', encoding='utf-8') as f:
            writers_data = json.load(f)
    
    # Load poets JSON
    poets_path = os.path.join(os.path.dirname(__file__), 'databases', 'poets.json')
    if os.path.exists(poets_path):
        with open(poets_path, 'r', encoding='utf-8') as f:
            poets_data = json.load(f)
    
    # Combine and process all authors
    all_authors = {}
    
    # Process writers
    for writer in writers_data:
        name = writer.get('name', '')
        # Skip if already processed (Kuvempu appears in both)
        if name not in all_authors:
            # Get Kannada name - use name field as fallback
            name_kannada = name  # Will use English name if Kannada not available
            # Try to get Kannada name from existing data or use English
            if name == 'Kuvempu':
                name_kannada = 'ಕುವೆಂಪು'
            elif name == 'U. R. Ananthamurthy':
                name_kannada = 'ಯು.ಆರ್. ಅನಂತಮೂರ್ತಿ'
            elif name == 'S. L. Bhyrappa':
                name_kannada = 'ಎಸ್.ಎಲ್. ಭೈರಪ್ಪ'
            elif name == 'Poornachandra Tejaswi':
                name_kannada = 'ಪೂರ್ಣಚಂದ್ರ ತೇಜಸ್ವಿ'
            elif name == 'Graama Seva Bhaagya (Bevina Seena Sharief)':
                name_kannada = 'ಬೆವಿನ ಸೀನ ಶರೀಫ್'
                name = 'Bevina Seena Sharief'  # Use simpler name
            
            biography = writer.get('biography', writer.get('contribution', ''))
            era = 'Modern'  # Default era
            if 'Navya' in biography or 'Navya' in writer.get('contribution', ''):
                era = 'Navya'
            elif 'Navodaya' in biography:
                era = 'Navodaya'
            
            # Determine image URL
            image_url = f"{name.lower().replace(' ', '_').replace('.', '')}.jpg"
            if name == 'Kuvempu':
                image_url = 'kuvempu.jpeg'
            elif name == 'Poornachandra Tejaswi':
                image_url = 'tejaswi.jpeg'
            
            all_authors[name] = {
                'name_kannada': name_kannada,
                'name_english': name,
                'biography': biography,
                'era': era,
                'image_url': image_url,
                'famous_works': writer.get('famous_works', []),
                'genres': writer.get('genres', []),
                'type': 'Writer'
            }
    
    # Process poets
    for poet in poets_data:
        name = poet.get('name', '')
        # Skip Kuvempu as already processed
        if name == 'Kuvempu':
            # Update Kuvempu with additional poetry info
            if name in all_authors:
                all_authors[name]['famous_poems'] = poet.get('famous_poems', [])
            continue
        
        # Get Kannada name
        name_kannada = name
        if name == 'D. R. Bendre':
            name_kannada = 'ಡಿ. ಆರ್. ಬೇಂದ್ರೆ'
        elif name == 'Masti Venkatesha Iyengar':
            name_kannada = 'ಮಾಸ್ತಿ ವೆಂಕಟೇಶ ಅಯ್ಯಂಗಾರ್'
        elif name == 'K. S. Narasimhaswamy':
            name_kannada = 'ಕೆ. ಎಸ್. ನರಸಿಂಹಸ್ವಾಮಿ'
        elif name == 'G. S. Shivarudrappa':
            name_kannada = 'ಜಿ. ಎಸ್. ಶಿವರುದ್ರಪ್ಪ'
        
        biography = poet.get('biography', poet.get('contribution', ''))
        era = 'Modern'
        if 'Navodaya' in biography:
            era = 'Navodaya'
        
        # Determine image URL
        image_url = f"{name.lower().replace(' ', '_').replace('.', '')}.jpg"
        
        all_authors[name] = {
            'name_kannada': name_kannada,
            'name_english': name,
            'biography': biography,
            'era': era,
            'image_url': image_url,
            'famous_works': poet.get('famous_works', []),
            'famous_poems': poet.get('famous_poems', []),
            'genres': [],  # Poets don't have genres in the JSON
            'type': 'Poet'
        }
    
    # Insert authors and get IDs
    author_ids = {}
    for author_name, author_info in all_authors.items():
        author_ids[author_name] = get_or_create_author(
            db, 
            author_info['name_kannada'],
            author_info['name_english'],
            author_info['biography'],
            author_info['era'],
            author_info['image_url']
        )
    
    # Insert works
    works_count = 0
    for author_name, author_info in all_authors.items():
        author_id = author_ids[author_name]
        
        # Add famous works (novels, stories, etc.)
        for work_title in author_info.get('famous_works', []):
            # Check if work already exists
            existing_work = db.execute('SELECT work_id FROM Work WHERE title_english = ?', (work_title,)).fetchone()
            if not existing_work:
                # Determine work type
                work_type = 'Novel'
                if 'Play' in work_title or 'Drama' in author_info.get('genres', []):
                    work_type = 'Play'
                elif 'Short Stories' in author_info.get('genres', []):
                    work_type = 'Short Story'
                
                # Use English title for Kannada title if not available
                db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
                          (author_id, work_title, work_title, work_type, f"A notable work by {author_info['name_english']}."))
                works_count += 1
        
        # Add famous poems
        for poem_title in author_info.get('famous_poems', []):
            # Check if work already exists
            existing_work = db.execute('SELECT work_id FROM Work WHERE title_english = ?', (poem_title,)).fetchone()
            if not existing_work:
                db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis) VALUES (?, ?, ?, ?, ?)',
                          (author_id, poem_title, poem_title, 'Poetry', f"A famous poem by {author_info['name_english']}."))
                works_count += 1
    
    db.commit()
    print(f"Populated the database with {len(all_authors)} authors and {works_count} works.")

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

    def get_id(self):
        return str(self.id)

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
    # Fetch works along with author name and author image URL
    works = db.execute('''
        SELECT 
            Work.*, 
            Author.name_kannada as author_kannada, 
            Author.name_english as author_english,
            Author.image_url as author_image_url
        FROM Work
        JOIN Author ON Work.author_id = Author.author_id
        ORDER BY Work.work_id DESC
    ''').fetchall()
    return render_template('index.html', works=works)

@app.route('/work/<int:work_id>', methods=['GET', 'POST'])
def work_details(work_id):
    """Shows details for a single work, its reviews, and the review form."""
    db = get_db()
    work = db.execute('''
        SELECT 
            Work.*, 
            Author.name_kannada as author_kannada, 
            Author.name_english as author_english,
            Author.image_url as author_image_url
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
    
    # Check for existing review (for update functionality)
    user_review = None
    if current_user.is_authenticated:
        user_review = db.execute(
            'SELECT * FROM Review WHERE user_id = ? AND work_id = ?', 
            (current_user.id, work_id)
        ).fetchone()

    if form.validate_on_submit() and current_user.is_authenticated:
        try:
            if user_review:
                # Update existing review
                db.execute('''
                    UPDATE Review SET rating=?, review_text=?, date_read=?, date_logged=CURRENT_TIMESTAMP
                    WHERE review_id = ?
                ''', (form.rating.data, form.review_text.data, form.date_read.data, user_review['review_id']))
                flash('Your review has been updated!', 'success')
            else:
                # Insert new review
                db.execute('''
                    INSERT INTO Review (user_id, work_id, rating, review_text, date_read)
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_user.id, work_id, form.rating.data, form.review_text.data, form.date_read.data))
                flash('Your review has been logged!', 'success')

            db.commit()
            return redirect(url_for('work_details', work_id=work_id))
        except Exception as e:
            db.rollback()
            flash(f'Error logging review: {e}', 'danger')
    
    # Pre-fill form if user is logged in and has an existing review
    elif request.method == 'GET' and current_user.is_authenticated:
        if user_review:
            # Pre-populate form with existing data for editing
            form.rating.data = user_review['rating']
            form.review_text.data = user_review['review_text']
            # Convert date string to date object
            form.date_read.data = datetime.datetime.strptime(user_review['date_read'], '%Y-%m-%d').date()
        else:
            # Default date read for new review
            form.date_read.data = datetime.date.today()
        
    return render_template('work_details.html', work=work, reviews=reviews, form=form, user_review=user_review)

@app.route('/profile/<string:username>')
def user_profile(username):
    """Shows a user's profile and all their reviews."""
    db = get_db()
    user = db.execute('SELECT * FROM User WHERE username = ?', (username,)).fetchone()
    
    if user is None:
        abort(404)
        
    reviews = db.execute('''
        SELECT Review.*, Work.title_kannada, Work.title_english, Work.work_id
        FROM Review
        JOIN Work ON Review.work_id = Work.work_id
        WHERE Review.user_id = ?
        ORDER BY Review.date_read DESC
    ''', (user['user_id'],)).fetchall()
    
    return render_template('profile.html', user=user, reviews=reviews)

@app.route('/author/<int:author_id>')
def author_details(author_id):
    """Shows details for a single author and all their works."""
    db = get_db()
    author = db.execute('SELECT * FROM Author WHERE author_id = ?', (author_id,)).fetchone()

    if author is None:
        abort(404)

    works = db.execute('SELECT * FROM Work WHERE author_id = ?', (author_id,)).fetchall()

    return render_template('author.html', author=author, works=works)


# --- Auto-complete search ---
@app.route('/search-autocomplete')
def search_autocomplete():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    db = get_db()
    
    # Fetch Authors (English or Kannada name contains query)
    authors = db.execute(
        'SELECT author_id, name_kannada, name_english FROM Author WHERE name_kannada LIKE ? OR name_english LIKE ? LIMIT 5', 
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    
    # Fetch Works (English or Kannada title contains query)
    works = db.execute(
        'SELECT work_id, title_kannada, title_english FROM Work WHERE title_kannada LIKE ? OR title_english LIKE ? LIMIT 5', 
        (f'%{query}%', f'%{query}%')
    ).fetchall()

    suggestions = []
    for author in authors:
        suggestions.append({
            'label': f"Author: {author['name_english']} ({author['name_kannada']})", 
            'type': 'Author', 
            'url': url_for('author_details', author_id=author['author_id'])
        })
    for work in works:
        suggestions.append({
            'label': f"Work: {work['title_english']} ({work['title_kannada']})", 
            'type': 'Work', 
            'url': url_for('work_details', work_id=work['work_id'])
        })
        
    return jsonify(suggestions)


if __name__ == '__main__':
    app.run(debug=True)