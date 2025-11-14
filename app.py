import os
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash, jsonify, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
import datetime
import re

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
            json_obj = json.load(f)
            # Handle nested "authors" key if it exists
            writers_data = json_obj.get('authors', json_obj) if isinstance(json_obj, dict) else json_obj
    
    # Load poets JSON
    poets_path = os.path.join(os.path.dirname(__file__), 'databases', 'poets.json')
    if os.path.exists(poets_path):
        with open(poets_path, 'r', encoding='utf-8') as f:
            json_obj = json.load(f)
            # Handle nested "authors" or "poets" key if it exists
            poets_data = json_obj.get('poets', json_obj.get('authors', json_obj)) if isinstance(json_obj, dict) else json_obj
    
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
        author_genres = json.dumps(author_info.get('genres', []))  # Convert genres to JSON string

        # Add famous works (novels, stories, etc.)
        for work in author_info.get('famous_works', []):
            # Handle both string and object formats
            if isinstance(work, dict):
                work_title = work.get('title', '')
                work_description = work.get('short_description', '')
                # prefer per-work genre when present
                work_genre_field = work.get('genre', '')
            else:
                work_title = work
                work_description = ''
                work_genre_field = ''

            if not work_title:
                continue

            # Check if work already exists
            existing_work = db.execute('SELECT work_id FROM Work WHERE title_english = ?', (work_title,)).fetchone()
            if not existing_work:
                # Determine work type
                work_type = 'Novel'
                # if the work-level genre suggests poetry/play, prefer that
                if work_genre_field and ('poem' in work_genre_field.lower() or 'poetry' in work_genre_field.lower()):
                    work_type = 'Poetry'
                elif 'play' in work_genre_field.lower() or 'drama' in work_genre_field.lower():
                    work_type = 'Play'
                elif 'short' in work_genre_field.lower() or 'story' in work_genre_field.lower():
                    work_type = 'Short Story'
                else:
                    if 'Play' in work_title or 'Drama' in author_info.get('genres', []):
                        work_type = 'Play'
                    elif 'Short Stories' in author_info.get('genres', []):
                        work_type = 'Short Story'

                synopsis = work_description or f"A notable work by {author_info['name_english']}."
                # Build genres JSON: prefer work-level genre, else author genres
                if work_genre_field:
                    # split multi-part genre strings on comma or slash
                    parts = [p.strip() for p in re.split('[,/]', work_genre_field) if p.strip()]
                    work_genres_json = json.dumps(parts)
                else:
                    work_genres_json = author_genres

                # Use English title for Kannada title if not available
                db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis, genres) VALUES (?, ?, ?, ?, ?, ?)',
                          (author_id, work_title, work_title, work_type, synopsis, work_genres_json))
                works_count += 1

        # Add famous poems
        for poem in author_info.get('famous_poems', []):
            # Handle both string and object formats
            if isinstance(poem, dict):
                poem_title = poem.get('title', '')
                poem_description = poem.get('short_description', '')
                poem_genre_field = poem.get('genre', '')
            else:
                poem_title = poem
                poem_description = ''
                poem_genre_field = ''

            if not poem_title:
                continue

            # Check if work already exists
            existing_work = db.execute('SELECT work_id FROM Work WHERE title_english = ?', (poem_title,)).fetchone()
            if not existing_work:
                synopsis = poem_description or f"A famous poem by {author_info['name_english']}."
                # prefer work-level genre for poems
                if poem_genre_field:
                    parts = [p.strip() for p in re.split('[,/]', poem_genre_field) if p.strip()]
                    poem_genres_json = json.dumps(parts)
                else:
                    poem_genres_json = author_genres
                db.execute('INSERT INTO Work (author_id, title_kannada, title_english, type, synopsis, genres) VALUES (?, ?, ?, ?, ?, ?)',
                          (author_id, poem_title, poem_title, 'Poetry', synopsis, poem_genres_json))
                works_count += 1
    
    db.commit()
    print(f"Populated the database with {len(all_authors)} authors and {works_count} works.")

def populate_reviews():
    """Populate reviews for all works with ratings between 4 and 5."""
    import random
    db = get_db()
    
    # Get all works
    works = db.execute('SELECT work_id FROM Work').fetchall()
    
    # Get or create dummy users for reviews
    dummy_users = []
    user_names = ['BookLover', 'LiteraryFan', 'KannadaReader', 'PoetryEnthusiast', 'NovelAdmirer', 
                  'ClassicReader', 'ModernLitFan', 'StorySeeker', 'PageTurner', 'BookWorm']
    
    for username in user_names:
        user = db.execute('SELECT user_id FROM User WHERE username = ?', (username,)).fetchone()
        if not user:
            # Create dummy user with hashed password
            hashed = bcrypt.generate_password_hash('dummy123').decode('utf-8')
            db.execute('INSERT INTO User (username, email, password_hash) VALUES (?, ?, ?)',
                      (username, f'{username.lower()}@example.com', hashed))
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            user_id = user['user_id']
        dummy_users.append(user_id)
    
    # Sample review texts
    review_texts = [
        "A masterpiece of Kannada literature. Deeply moving and thought-provoking.",
        "Beautifully written with rich cultural insights. Highly recommended!",
        "One of the finest works I've read. The narrative is captivating.",
        "A profound exploration of human nature and society. Exceptional writing.",
        "This book left a lasting impression. The author's style is remarkable.",
        "An excellent read that captures the essence of Kannada culture.",
        "Brilliant storytelling with deep philosophical undertones.",
        "A must-read for anyone interested in Kannada literature.",
        "The characters are well-developed and the plot is engaging.",
        "Outstanding work that deserves to be read by everyone.",
        "Beautiful prose and meaningful themes throughout.",
        "A classic that stands the test of time.",
        "Thoughtful and inspiring. One of my favorites.",
        "The author's command over language is impressive.",
        "A wonderful book that I couldn't put down."
    ]
    
    # Populate reviews for each work
    reviews_added = 0
    for work in works:
        work_id = work['work_id']
        
        # Check existing reviews count
        existing_count = db.execute('SELECT COUNT(*) as count FROM Review WHERE work_id = ?', 
                                   (work_id,)).fetchone()['count']
        
        # Add 3-8 reviews per work (to create variation in popularity)
        num_reviews = random.randint(3, 8)
        
        for _ in range(num_reviews):
            # Random user
            user_id = random.choice(dummy_users)
            
            # Check if this user already reviewed this work
            existing_review = db.execute('SELECT review_id FROM Review WHERE user_id = ? AND work_id = ?',
                                        (user_id, work_id)).fetchone()
            if existing_review:
                continue
            
            # Rating between 4 and 5 (using 4 or 5 since rating is INTEGER)
            rating = random.choice([4, 4, 4, 5, 5])  # More 4s and 5s
            
            # Random review text (70% chance)
            review_text = random.choice(review_texts) if random.random() < 0.7 else None
            
            # Random date within last 30 days (more recent dates for "this week")
            # 40% chance of being in last 7 days for "Popular this week"
            if random.random() < 0.4:
                days_ago = random.randint(0, 7)
            else:
                days_ago = random.randint(8, 30)
            date_read = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
            
            # date_logged will be set automatically to CURRENT_TIMESTAMP, but we can also set it explicitly
            # to ensure reviews appear in "this week"
            date_logged = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat()
            
            db.execute('''
                INSERT INTO Review (user_id, work_id, rating, review_text, date_read, date_logged)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, work_id, rating, review_text, date_read, date_logged))
            reviews_added += 1
    
    db.commit()
    print(f"Populated {reviews_added} reviews for {len(works)} works.")

@app.cli.command('init')
def init_db_command():
    """Command to initialize the database: `flask init`"""
    init_db()
    print('Database initialization complete.')
    print('Run "flask populate-reviews" to add sample reviews to all works.')

@app.cli.command('populate-reviews')
def populate_reviews_command():
    """Command to populate reviews: `flask populate-reviews`"""
    populate_reviews()
    print('Reviews populated successfully.')

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
    """Homepage shows Popular This Week based on review count."""
    db = get_db()
    # Fetch popular works based on review count from the last 7 days
    popular_works = db.execute('''
        SELECT 
            Work.*, 
            Author.name_kannada as author_kannada, 
            Author.name_english as author_english,
            Author.image_url as author_image_url,
            COUNT(CASE WHEN Review.date_logged >= datetime('now', '-7 days') THEN Review.review_id END) as review_count,
            AVG(CASE WHEN Review.date_logged >= datetime('now', '-7 days') THEN Review.rating END) as avg_rating
        FROM Work
        JOIN Author ON Work.author_id = Author.author_id
        LEFT JOIN Review ON Work.work_id = Review.work_id
        GROUP BY Work.work_id
        HAVING review_count > 0
        ORDER BY review_count DESC, avg_rating DESC
        LIMIT 12
    ''').fetchall()
    
    # If not enough works with recent reviews, fall back to all-time popular
    if len(popular_works) < 6:
        popular_works = db.execute('''
            SELECT 
                Work.*, 
                Author.name_kannada as author_kannada, 
                Author.name_english as author_english,
                Author.image_url as author_image_url,
                COUNT(Review.review_id) as review_count,
                AVG(Review.rating) as avg_rating
            FROM Work
            JOIN Author ON Work.author_id = Author.author_id
            LEFT JOIN Review ON Work.work_id = Review.work_id
            GROUP BY Work.work_id
            HAVING review_count > 0
            ORDER BY review_count DESC, avg_rating DESC
            LIMIT 12
        ''').fetchall()
    
    return render_template('index.html', works=popular_works)

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
        SELECT 
            Review.*, 
            Work.title_kannada, 
            Work.title_english, 
            Work.work_id,
            Author.name_kannada,
            Author.name_english,
            Author.author_id
        FROM Review
        JOIN Work ON Review.work_id = Work.work_id
        JOIN Author ON Work.author_id = Author.author_id
        WHERE Review.user_id = ?
        ORDER BY Review.date_read DESC
    ''', (user['user_id'],)).fetchall()
    
    return render_template('profiles.html', user=user, reviews=reviews)

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
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 1:
        return jsonify([])
    
    db = get_db()
    
    # Fetch Authors (English or Kannada name contains query) - prioritize exact matches
    authors_exact = db.execute(
        '''SELECT author_id, name_kannada, name_english FROM Author 
           WHERE LOWER(name_english) = ? OR LOWER(name_kannada) = ? LIMIT 3''', 
        (query, query)
    ).fetchall()
    
    authors_partial = db.execute(
        '''SELECT author_id, name_kannada, name_english FROM Author 
           WHERE (LOWER(name_kannada) LIKE ? OR LOWER(name_english) LIKE ?)
           AND author_id NOT IN (SELECT author_id FROM Author WHERE LOWER(name_english) = ? OR LOWER(name_kannada) = ?)
           LIMIT 5''', 
        (f'%{query}%', f'%{query}%', query, query)
    ).fetchall()
    
    # Fetch Works (English or Kannada title contains query) - prioritize exact matches
    works_exact = db.execute(
        '''SELECT work_id, title_kannada, title_english FROM Work 
           WHERE LOWER(title_english) = ? OR LOWER(title_kannada) = ? LIMIT 3''', 
        (query, query)
    ).fetchall()
    
    works_partial = db.execute(
        '''SELECT work_id, title_kannada, title_english FROM Work 
           WHERE (LOWER(title_kannada) LIKE ? OR LOWER(title_english) LIKE ?)
           AND work_id NOT IN (SELECT work_id FROM Work WHERE LOWER(title_english) = ? OR LOWER(title_kannada) = ?)
           LIMIT 7''', 
        (f'%{query}%', f'%{query}%', query, query)
    ).fetchall()

    suggestions = []
    
    # Add exact matches first (higher priority)
    for author in authors_exact:
        suggestions.append({
            'label': f"Author: {author['name_english']} ({author['name_kannada']})", 
            'type': 'Author', 
            'url': url_for('author_details', author_id=author['author_id']),
            'priority': 1
        })
    
    for work in works_exact:
        suggestions.append({
            'label': f"Work: {work['title_english']} ({work['title_kannada']})", 
            'type': 'Work', 
            'url': url_for('work_details', work_id=work['work_id']),
            'priority': 1
        })
    
    # Add partial matches
    for author in authors_partial:
        suggestions.append({
            'label': f"Author: {author['name_english']} ({author['name_kannada']})", 
            'type': 'Author', 
            'url': url_for('author_details', author_id=author['author_id']),
            'priority': 2
        })
    
    for work in works_partial:
        suggestions.append({
            'label': f"Work: {work['title_english']} ({work['title_kannada']})", 
            'type': 'Work', 
            'url': url_for('work_details', work_id=work['work_id']),
            'priority': 2
        })
    
    # Sort by priority, then limit to 10 results
    suggestions.sort(key=lambda x: x.get('priority', 3))
    suggestions = suggestions[:10]
        
    return jsonify(suggestions)

# --- Search Results Page ---
@app.route('/search')
def search_results():
    """Search results page showing all matching works and authors."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('search_results.html', query='', works=[], authors=[])
    
    db = get_db()
    
    # Search for authors
    authors = db.execute('''
        SELECT author_id, name_kannada, name_english, biography, era, image_url
        FROM Author 
        WHERE LOWER(name_kannada) LIKE ? OR LOWER(name_english) LIKE ?
        ORDER BY 
            CASE 
                WHEN LOWER(name_english) = ? OR LOWER(name_kannada) = ? THEN 1
                WHEN LOWER(name_english) LIKE ? OR LOWER(name_kannada) LIKE ? THEN 2
                ELSE 3
            END,
            name_english
        LIMIT 20
    ''', (f'%{query.lower()}%', f'%{query.lower()}%', query.lower(), query.lower(), f'{query.lower()}%', f'{query.lower()}%')).fetchall()
    
    # Search for works
    works = db.execute('''
        SELECT 
            Work.*,
            Author.name_kannada as author_kannada,
            Author.name_english as author_english,
            Author.image_url as author_image_url,
            COUNT(Review.review_id) as review_count,
            AVG(Review.rating) as avg_rating
        FROM Work
        JOIN Author ON Work.author_id = Author.author_id
        LEFT JOIN Review ON Work.work_id = Review.work_id
        WHERE LOWER(Work.title_kannada) LIKE ? OR LOWER(Work.title_english) LIKE ?
           OR LOWER(Author.name_english) LIKE ? OR LOWER(Author.name_kannada) LIKE ?
        GROUP BY Work.work_id
        ORDER BY 
            CASE 
                WHEN LOWER(Work.title_english) = ? OR LOWER(Work.title_kannada) = ? THEN 1
                WHEN LOWER(Work.title_english) LIKE ? OR LOWER(Work.title_kannada) LIKE ? THEN 2
                ELSE 3
            END,
            review_count DESC,
            avg_rating DESC
        LIMIT 50
    ''', (f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%',
          query.lower(), query.lower(), f'{query.lower()}%', f'{query.lower()}%')).fetchall()
    
    return render_template('search_results.html', query=query, works=works, authors=authors)

# load writer.json once at startup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRITER_JSON_PATH = os.path.join(BASE_DIR, "writer.json")

def load_writers():
    try:
        with open(WRITER_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

WRITERS = load_writers()

def get_author_ids_by_genre(genre):
    if not genre:
        return set()
    genre_l = genre.strip().lower()
    matches = set()
    for w in WRITERS:
        genres = w.get("genres", []) or []
        genres_l = [g.strip().lower() for g in genres]
        if any(genre_l == g or genre_l in g for g in genres_l):
            if "author_id" in w:
                try:
                    matches.add(int(w["author_id"]))
                except Exception:
                    pass
            else:
                matches.add(w.get("name") or w.get("name_english") or "")
    return matches

def query_db(query, args=(), one=False):
    con = getattr(g, "_database", None)
    if con is None:
        con = g._database = sqlite3.connect(os.path.join(BASE_DIR, "kannada_letterboxd.db"))
        con.row_factory = sqlite3.Row
    cur = con.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/genre_search")
def genre_search():
    genre = request.args.get("genre", "").strip()
    if not genre:
        flash("Please enter a genre to search.", "info")
        return redirect(request.referrer or url_for("homepage"))

    genre_lower = genre.lower()
    db = get_db()
    
    # Search for works where the genres JSON field contains the requested genre
    # Only search in work type and genres, not author names
    works = db.execute("""
        SELECT DISTINCT 
            Work.*, 
            Author.name_kannada, 
            Author.name_english,
            Author.author_id,
            Author.image_url as author_image_url,
            COUNT(Review.review_id) as review_count,
            AVG(Review.rating) as avg_rating
        FROM Work 
        JOIN Author ON Work.author_id = Author.author_id
        LEFT JOIN Review ON Work.work_id = Review.work_id
        WHERE 
            lower(Work.type) LIKE ? 
            OR lower(Work.genres) LIKE ?
        GROUP BY Work.work_id
        ORDER BY Work.title_english ASC
    """, (f"%{genre_lower}%", f"%{genre_lower}%")).fetchall()
    
    # If no results with genre search, try broader search
    if not works:
        works = db.execute("""
            SELECT 
                Work.*, 
                Author.name_kannada, 
                Author.name_english,
                Author.author_id,
                Author.image_url as author_image_url,
                COUNT(Review.review_id) as review_count,
                AVG(Review.rating) as avg_rating
            FROM Work 
            JOIN Author ON Work.author_id = Author.author_id
            LEFT JOIN Review ON Work.work_id = Review.work_id
            WHERE 
                lower(Work.title_english) LIKE ? 
                OR lower(Work.title_kannada) LIKE ?
                OR lower(Work.synopsis) LIKE ?
            GROUP BY Work.work_id
            ORDER BY Work.title_english ASC
        """, (f"%{genre_lower}%", f"%{genre_lower}%", f"%{genre_lower}%")).fetchall()

    return render_template("genre_results.html", genre=genre, works=works)

@app.route("/genre/<genre>")
def genre_page(genre):
    return redirect(url_for("genre_search", genre=genre))


if __name__ == '__main__':
    app.run(debug=True)