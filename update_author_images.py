#!/usr/bin/env python3
"""
Script to update author image URLs in the database.
Run this script to update existing author records with image URLs.
"""

import sqlite3

DATABASE = 'kannada_letterboxd.db'

def update_author_images():
    """Update author records with image URLs."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Update Kuvempu
        cursor.execute("UPDATE Author SET image_url = 'kuvempu.jpeg' WHERE name_english = 'Kuvempu'")
        kuvempu_updated = cursor.rowcount
        
        # Update Poornachandra Tejaswi
        cursor.execute("UPDATE Author SET image_url = 'tejaswi.jpeg' WHERE name_english = 'Poornachandra Tejaswi'")
        tejaswi_updated = cursor.rowcount
        
        conn.commit()
        
        print(f"✓ Updated {kuvempu_updated} record(s) for Kuvempu")
        print(f"✓ Updated {tejaswi_updated} record(s) for Poornachandra Tejaswi")
        print("\n✓ Database updated successfully!")
        print("  Refresh your browser to see the author images on the homepage.")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error updating database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_author_images()

