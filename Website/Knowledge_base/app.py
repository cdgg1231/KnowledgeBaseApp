import os
import datetime
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
import pyodbc

# Flask App
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuration
UPLOAD_FOLDER = './static/documents'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database Configuration
db_database = 'KnowledgeBaseDB'
db_user = 'dbuser'
db_password = 'admin'
db_engine = '.\\SQLEXPRESS'

# Database Connection
def connect_to_db():
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_engine};'
            f'DATABASE={db_database};'
            f'UID={db_user};'
            f'PWD={db_password}'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

# Routes

@app.route('/')
def home():
    # Fetch all documents from the database
    conn = connect_to_db()
    documents = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Title, FilePath, UploadDate, Summary FROM KnowledgeBase")
            documents = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching documents: {e}", "danger")
        finally:
            conn.close()
    return render_template('home.html', documents=documents)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Collect form data
        title = request.form.get('title')
        keywords = request.form.get('keywords')
        summary = request.form.get('summary')
        file = request.files['file']

        if not title or not file:
            flash("Title and File are required!", "danger")
            return redirect(url_for('upload'))

        # Save file to upload folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Convert to relative path for database storage
        file_path = os.path.relpath(file_path, start=os.getcwd())

        # Insert metadata into the database
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO KnowledgeBase (Title, FilePath, Keywords, UploadDate, Summary)
                    VALUES (?, ?, ?, ?, ?)
                """, title, file_path, keywords, datetime.datetime.now(), summary)
                conn.commit()
                flash("Document uploaded successfully!", "success")
            except Exception as e:
                flash(f"Error uploading document: {e}", "danger")
            finally:
                conn.close()
        return redirect(url_for('upload'))
    return render_template('upload.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        search_query = request.form.get('query')

        if not search_query:
            flash("Please enter a search query!", "danger")
            return redirect(url_for('search'))

        # Query database
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT Title, FilePath, UploadDate, Summary
                    FROM KnowledgeBase
                    WHERE Title LIKE ? OR Keywords LIKE ?
                """, f"%{search_query}%", f"%{search_query}%")
                results = cursor.fetchall()
            except Exception as e:
                flash(f"Error searching documents: {e}", "danger")
            finally:
                conn.close()
    return render_template('search.html', results=results)

@app.route('/view', methods=['GET'])
def view_document():
    file_path = request.args.get('file_path')
    if not file_path:
        flash("No file specified", "danger")
        return redirect(url_for('search'))

    try:
        # Normalize and resolve file path
        file_path = os.path.normpath(file_path)  # Normalize slashes
        absolute_path = os.path.join(os.getcwd(), file_path)  # Convert to absolute path

        # Ensure the file exists
        if not os.path.isfile(absolute_path):
            flash("File not found", "danger")
            return redirect(url_for('search'))

        # Determine the file extension
        _, file_extension = os.path.splitext(absolute_path)
        if file_extension in ['.txt', '.html']:
            # Read and display text or HTML content
            with open(absolute_path, 'r') as file:
                content = file.read()
            return render_template('view.html', content=content, file_name=os.path.basename(absolute_path))
        elif file_extension == '.pdf':
            # Serve PDF files inline
            return send_file(absolute_path, as_attachment=False)
        else:
            flash("Unsupported file format for viewing", "warning")
            return redirect(url_for('search'))
    except Exception as e:
        flash(f"Error viewing file: {e}", "danger")
        return redirect(url_for('search'))

if __name__ == '__main__':
    app.run(debug=True)
