-- SQL script to update author image URLs
-- Run this in your SQLite database

UPDATE Author SET image_url = 'kuvempu.jpeg' WHERE name_english = 'Kuvempu';
UPDATE Author SET image_url = 'tejaswi.jpeg' WHERE name_english = 'Poornachandra Tejaswi';

