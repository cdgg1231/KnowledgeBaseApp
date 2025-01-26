import os
import datetime
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

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
import hashlib
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Hash the input password
        password_hash = hashlib.sha256(password.encode()).hexdigest().upper()
        print(f"Input password hash: {password_hash}")

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT Password, AccessLevel FROM Users WHERE Username = ?", username)
                user = cursor.fetchone()
                print(f"Fetched user: {user}")

                if user and user[0] == password_hash:  # Compare hash directly
                    session['username'] = username
                    session['access_level'] = user[1]
                    flash("Login successful!", "success")
                    return redirect(url_for('home'))
                else:
                    flash("Invalid username or password", "danger")
            except Exception as e:
                flash(f"Error during login: {e}", "danger")
            finally:
                conn.close()
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.route('/')
def home():
    # Check if user is logged in
    if 'username' not in session:
        flash("Please log in to access the system.", "warning")
        return redirect(url_for('login'))

    # Fetch all documents from the database
    conn = connect_to_db()
    documents = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DocumentID, Title, FilePath, UploadDate, Summary FROM KnowledgeBase")
            documents = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching documents: {e}", "danger")
        finally:
            conn.close()
    return render_template('home.html', documents=documents)

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    # Restrict access to admins only
    if 'access_level' not in session or session['access_level'] != "Admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Get user details from the form
        username = request.form.get('username')
        password = request.form.get('password')
        access_level = request.form.get('access_level')

        if not username or not password or not access_level:
            flash("All fields are required!", "danger")
            return redirect(url_for('create_user'))

        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest().upper()

        # Insert the new user into the database
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Users (Username, Password, AccessLevel)
                    VALUES (?, ?, ?)
                """, username, password_hash, access_level)
                conn.commit()
                flash("User created successfully!", "success")
            except Exception as e:
                flash(f"Error creating user: {e}", "danger")
            finally:
                conn.close()
        return redirect(url_for('create_user'))
    
    return render_template('create_user.html')



@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # # Restrict access to admins only
    # if 'access_level' not in session or session['access_level'] not in ["Admin"]:
    #     flash("You do not have permission to access this page.", "danger")
    #     return redirect(url_for('home'))

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
                    SELECT DocumentID, Title, FilePath, UploadDate, Summary
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

@app.route('/edit_document/<int:document_id>', methods=['GET', 'POST'])
def edit_document(document_id):
    # Restrict access to admins only
    if 'access_level' not in session or session['access_level'] != "Admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            # Fetch document details
            cursor.execute("SELECT Title, FilePath, Keywords, Summary FROM KnowledgeBase WHERE DocumentID = ?", document_id)
            document = cursor.fetchone()
        except Exception as e:
            flash(f"Error fetching document: {e}", "danger")
            return redirect(url_for('home'))
        finally:
            conn.close()

    if request.method == 'POST':
        # Update the document
        title = request.form.get('title')
        keywords = request.form.get('keywords')
        summary = request.form.get('summary')
        file = request.files['file']

        if not title:
            flash("Title is required!", "danger")
            return redirect(url_for('edit_document', document_id=document_id))

        # Save the new file if uploaded
        file_path = document[1]
        if file:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            file_path = os.path.relpath(file_path, start=os.getcwd())

        # Update the database
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE KnowledgeBase
                    SET Title = ?, FilePath = ?, Keywords = ?, Summary = ?, UploadDate = ?
                    WHERE DocumentID = ?
                """, title, file_path, keywords, summary, datetime.datetime.now(), document_id)
                conn.commit()
                flash("Document updated successfully!", "success")
            except Exception as e:
                flash(f"Error updating document: {e}", "danger")
            finally:
                conn.close()
        return redirect(url_for('home'))

    return render_template('edit_document.html', document=document)


if __name__ == '__main__':
    app.run(debug=True)
