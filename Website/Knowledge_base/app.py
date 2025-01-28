import os
import datetime
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

import os
import pyodbc
from dotenv import load_dotenv

# Flask App
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuration
UPLOAD_FOLDER = './static/documents'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

import os
import pyodbc

# Fetch credentials from environment variables
db_database = os.getenv('DB_DATABASE')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_engine = os.getenv('DB_ENGINE')

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
    tickets = []
    if conn:
        try:
            cursor = conn.cursor()
            # Fetch documents
            cursor.execute("SELECT DocumentID, Title, FilePath, UploadDate, Summary FROM KnowledgeBase")
            documents = cursor.fetchall()

            # Fetch open tickets with username and job site
            cursor.execute("""
                SELECT 
                    t.TicketID, 
                    t.CreatedAt, 
                    t.IssueTitle, 
                    t.JobSite, 
                    u.Username
                FROM Tickets t
                LEFT JOIN Users u ON t.AssignedTo = u.UserID
                WHERE t.Status = 'Open'
            """)
            tickets = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching data: {e}", "danger")
        finally:
            conn.close()
    return render_template('home.html', documents=documents, tickets=tickets)




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

@app.route('/new_ticket', methods=['GET', 'POST'])
def new_ticket():
    search_results = []
    if request.method == 'POST':
        if 'search_query' in request.form:  # If the form is a search request
            search_query = request.form.get('search_query')
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT TicketID, IssueTitle, CreatedAt, Status, CloseAt
                        FROM Tickets
                        WHERE IssueTitle LIKE ?
                    """, f"%{search_query}%")
                    search_results = cursor.fetchall()
                except Exception as e:
                    flash(f"Error searching tickets: {e}", "danger")
                finally:
                    conn.close()
        else:  # If the form is for creating a ticket
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email')
            job_site = request.form.get('job_site')
            issue_title = request.form.get('issue_title')
            description = request.form.get('description')
            steps_taken = request.form.get('steps_taken')
            document_id = request.form.get('document_id')
            assigned_to = request.form.get('assigned_to')
            file = request.files['file']

            # Save file
            file_path = None
            if file:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                file_path = os.path.relpath(file_path, start=os.getcwd())

            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Tickets (Name, Phone, Email, JobSite, IssueTitle, Issue, StepsTaken, DocumentID, AssignedTo, FilePath)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, name, phone, email, job_site, issue_title, description, steps_taken, document_id, assigned_to, file_path)
                    conn.commit()
                    flash("Ticket created successfully!", "success")
                except Exception as e:
                    flash(f"Error creating ticket: {e}", "danger")
                finally:
                    conn.close()
            return redirect(url_for('home'))
    
    conn = connect_to_db()
    documents = []
    users = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DocumentID, Title FROM KnowledgeBase")
            documents = cursor.fetchall()
            cursor.execute("SELECT UserID, Username FROM Users")
            users = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching data: {e}", "danger")
        finally:
            conn.close()
    
    return render_template('new_ticket.html', documents=documents, users=users, search_results=search_results)



@app.route('/view_tickets')
def view_tickets():
    conn = connect_to_db()
    tickets = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Tickets")
            tickets = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching tickets: {e}", "danger")
        finally:
            conn.close()
    return render_template('view_tickets.html', tickets=tickets)

@app.route('/search_tickets', methods=['GET', 'POST'])
def search_tickets():
    results = []
    search_query = None

    if request.method == 'POST':
        search_query = request.form.get('query')

        if not search_query:
            flash("Please enter a search query!", "danger")
            return redirect(url_for('search_tickets'))

        # Query database for tickets matching the search
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT TicketID, IssueTitle, CreatedAt, Status
                    FROM Tickets
                    WHERE IssueTitle LIKE ? OR JobSite LIKE ?
                """, f"%{search_query}%", f"%{search_query}%")
                results = cursor.fetchall()
            except Exception as e:
                flash(f"Error searching tickets: {e}", "danger")
            finally:
                conn.close()

    return render_template('search_tickets.html', results=results, search_query=search_query)

@app.route('/edit_ticket/<int:ticket_id>', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    conn = connect_to_db()
    ticket = None
    users = []
    if conn:
        try:
            cursor = conn.cursor()
            if request.method == 'POST':
                # Update the ticket
                issue_title = request.form.get('issue_title')
                description = request.form.get('description')
                steps_taken = request.form.get('steps_taken')
                job_site = request.form.get('job_site')
                assigned_to = request.form.get('assigned_to')
                status = request.form.get('status')
                cursor.execute("""
                    UPDATE Tickets
                    SET IssueTitle = ?, Issue = ?, StepsTaken = ?, JobSite = ?, AssignedTo = ?, Status = ?
                    WHERE TicketID = ?
                """, issue_title, description, steps_taken, job_site, assigned_to, status, ticket_id)
                conn.commit()
                flash("Ticket updated successfully!", "success")
                return redirect(url_for('home'))

            # Fetch ticket details for editing
            cursor.execute("""
                SELECT TicketID, IssueTitle, Issue, StepsTaken, JobSite, AssignedTo, Status, CloseAt
                FROM Tickets
                WHERE TicketID = ?
            """, ticket_id)
            ticket = cursor.fetchone()

            # Fetch users for the dropdown
            cursor.execute("SELECT UserID, Username FROM Users")
            users = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching or updating ticket: {e}", "danger")
        finally:
            conn.close()
    return render_template('edit_ticket.html', ticket=ticket, users=users)

@app.route('/close_ticket/<int:ticket_id>', methods=['POST'])
def close_ticket(ticket_id):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            # Update the CloseAt column to the current timestamp
            cursor.execute("""
                UPDATE Tickets
                SET Status = 'Closed', CloseAt = ?
                WHERE TicketID = ?
            """, datetime.datetime.now(), ticket_id)
            conn.commit()
            flash("Ticket closed successfully!", "success")
        except Exception as e:
            flash(f"Error closing ticket: {e}", "danger")
        finally:
            conn.close()
    else:
        flash("Failed to connect to the database.", "danger")

    return redirect(url_for('home'))


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
