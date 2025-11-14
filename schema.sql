DROP TABLE IF EXISTS User;
DROP TABLE IF EXISTS Author;
DROP TABLE IF EXISTS Work;
DROP TABLE IF EXISTS Review;
DROP TABLE IF EXISTS Wishlist;

CREATE TABLE User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE Author (
    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_kannada TEXT NOT NULL,
    name_english TEXT NOT NULL,
    biography TEXT,
    image_url TEXT, -- e.g., 'kuvempu.jpg'
    era TEXT
);

CREATE TABLE Work (
    work_id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    title_kannada TEXT NOT NULL,
    title_english TEXT NOT NULL,
    synopsis TEXT,
    cover_image_url TEXT, -- e.g., 'kanooru_heggadithi.jpg'
    type TEXT, -- 'Novel', 'Poetry', 'Play'
    genres TEXT, -- JSON array of genres, e.g., '["Novel", "Social"]'
    FOREIGN KEY (author_id) REFERENCES Author (author_id)
);

CREATE TABLE Review (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    work_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,  -- Rating from 1 to 5
    review_text TEXT,         -- The written review (can be empty)
    date_read DATE NOT NULL,  -- The "diary date"
    date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User (user_id),
    FOREIGN KEY (work_id) REFERENCES Work (work_id)
);

CREATE TABLE Wishlist (
    wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    work_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User (user_id),
    FOREIGN KEY (work_id) REFERENCES Work (work_id),
    UNIQUE(user_id, work_id)
);