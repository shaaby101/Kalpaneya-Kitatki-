# Troubleshooting Guide

## Changes Not Appearing?

### 1. Restart Flask App
If your Flask app is running, you need to restart it to pick up code changes:

**In your terminal where Flask is running:**
- Press `Ctrl+C` to stop the server
- Start it again with: `python app.py` or `flask run`

### 2. Clear Browser Cache
Your browser might be showing cached files:

**Chrome/Edge:**
- Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) for hard refresh
- Or press `F12` → Right-click refresh button → "Empty Cache and Hard Reload"

**Firefox:**
- Press `Ctrl+F5` for hard refresh
- Or `Ctrl+Shift+Delete` → Clear cache

### 3. Populate Reviews
If "Popular This Week" is empty, you need to populate reviews:

```bash
flask populate-reviews
```

### 4. Check for Errors
Check your Flask terminal for any error messages. Common issues:
- Import errors
- Database connection errors
- Template not found errors

### 5. Verify Files Are Saved
Make sure all files are saved in your editor before restarting Flask.

