import os
import datetime
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session
import psycopg2  # Use psycopg2 instead of pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.dev")

# Fetch PostgreSQL database credentials
DATABASE_URL = os.getenv("DATABASE_URL")

# Flask App
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Load secret key from env

# Configuration
UPLOAD_FOLDER = './static/documents'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ PostgreSQL Database Connection Function
def connect_to_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        print("✅ Successfully connected to PostgreSQL database.")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

# ✅ Test connection at startup (proper indentation)
conn = connect_to_db()
if conn:
    conn.close()

    
    # Test connection at startup
conn = connect_to_db()
if conn:
    conn.close()

# ------------------------------------ ROUTES ------------------------------------

from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT password, accesslevel FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()

                # Debugging output
                print(f"🔍 Fetched user from DB: {user}")

                if user:
                    stored_password_hash = user[0]

                    # Debugging: Compare the stored hash with entered password
                    print(f"🔍 Stored Hash: {stored_password_hash}")
                    print(f"🔍 Entered Password: {password}")
                    print(f"🔍 Hash Check Result: {check_password_hash(stored_password_hash, password)}")

                    if check_password_hash(stored_password_hash, password):
                        session['username'] = username
                        session['access_level'] = user[1]
                        flash("✅ Login successful!", "success")
                        return redirect(url_for('home'))
                    else:
                        flash("❌ Invalid username or password", "danger")
                else:
                    flash("❌ User not found", "danger")
            except Exception as e:
                flash(f"⚠️ Error during login: {e}", "danger")

    return render_template('login.html')


# Generate a new hash for "user123"
from werkzeug.security import generate_password_hash

# Force pbkdf2:sha256 instead of scrypt
hashed_password = generate_password_hash("user123", method="pbkdf2:sha256")

print("🔑 Corrected Hashed Password:", hashed_password)







@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' not in session:
        flash("Please log in to access the system.", "warning")
        return redirect(url_for('login'))

    conn = connect_to_db()
    documents, tickets = [], []
    
    if conn:
        try:
            cursor = conn.cursor()

            # ✅ Corrected Queries for PostgreSQL
            cursor.execute("SELECT DocumentID, Title, FilePath, UploadDate, Summary FROM KnowledgeBase")
            documents = cursor.fetchall()

            cursor.execute("""
                SELECT t.TicketID, t.CreatedAt, t.IssueTitle, t.JobSite, u.Username
                FROM Tickets t
                LEFT JOIN Users u ON t.AssignedTo = u.UserID
                WHERE t.Status = 'Open'
            """)
            tickets = cursor.fetchall()

            cursor.close()
        except Exception as e:
            flash(f"Error fetching data: {e}", "danger")
        finally:
            conn.close()

    return render_template('home.html', documents=documents, tickets=tickets)

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if 'access_level' not in session or session['access_level'] != "Admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        access_level = request.form.get('access_level')

        if not username or not password or not access_level:
            flash("All fields are required!", "danger")
            return redirect(url_for('create_user'))

        # ✅ Hash password correctly
        password_hash = generate_password_hash(password)

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Users (Username, Password, AccessLevel)
                    VALUES (%s, %s, %s)
                """, (username, password_hash, access_level))
                conn.commit()
                cursor.close()
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
        if 'search_query' in request.form:
            search_query = request.form.get('search_query')
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT TicketID, IssueTitle, CreatedAt, Status, CloseAt
                        FROM Tickets
                        WHERE IssueTitle LIKE %s
                    """, (f"%{search_query}%",))
                    search_results = cursor.fetchall()
                    cursor.close()
                except Exception as e:
                    flash(f"Error searching tickets: {e}", "danger")
                finally:
                    conn.close()
        else:
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, phone, email, job_site, issue_title, description, steps_taken, document_id, assigned_to, file_path))
                    conn.commit()
                    cursor.close()
                    flash("Ticket created successfully!", "success")
                except Exception as e:
                    flash(f"Error creating ticket: {e}", "danger")
                finally:
                    conn.close()
            return redirect(url_for('home'))

    return render_template('new_ticket.html', search_results=search_results)



@app.route('/view_tickets')
def view_tickets():
    conn = connect_to_db()
    tickets = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Tickets")
            tickets = cursor.fetchall()
            cursor.close()
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

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT TicketID, IssueTitle, CreatedAt, Status
                    FROM Tickets
                    WHERE IssueTitle ILIKE %s OR JobSite ILIKE %s
                """, (f"%{search_query}%", f"%{search_query}%"))
                results = cursor.fetchall()
                cursor.close()
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
                issue_title = request.form.get('issue_title')
                description = request.form.get('description')
                steps_taken = request.form.get('steps_taken')
                job_site = request.form.get('job_site')
                assigned_to = request.form.get('assigned_to')
                status = request.form.get('status')

                cursor.execute("""
                    UPDATE Tickets
                    SET IssueTitle = %s, Issue = %s, StepsTaken = %s, JobSite = %s, AssignedTo = %s, Status = %s
                    WHERE TicketID = %s
                """, (issue_title, description, steps_taken, job_site, assigned_to, status, ticket_id))
                conn.commit()
                cursor.close()
                flash("Ticket updated successfully!", "success")
                return redirect(url_for('home'))

            cursor.execute("""
                SELECT TicketID, IssueTitle, Issue, StepsTaken, JobSite, AssignedTo, Status, CloseAt
                FROM Tickets
                WHERE TicketID = %s
            """, (ticket_id,))
            ticket = cursor.fetchone()

            cursor.execute("SELECT UserID, Username FROM Users")
            users = cursor.fetchall()
            cursor.close()
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
            cursor.execute("""
                UPDATE Tickets
                SET Status = 'Closed', CloseAt = %s
                WHERE TicketID = %s
            """, (datetime.datetime.now(), ticket_id))
            conn.commit()
            cursor.close()
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
    if request.method == 'POST':
        title = request.form.get('title')
        keywords = request.form.get('keywords')
        summary = request.form.get('summary')
        file = request.files['file']

        if not title or not file:
            flash("Title and File are required!", "danger")
            return redirect(url_for('upload'))

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        file_path = os.path.relpath(file_path, start=os.getcwd())

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO KnowledgeBase (Title, FilePath, Keywords, UploadDate, Summary)
                    VALUES (%s, %s, %s, %s, %s)
                """, (title, file_path, keywords, datetime.datetime.now(), summary))
                conn.commit()
                cursor.close()
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

        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DocumentID, Title, FilePath, UploadDate, Summary
                    FROM KnowledgeBase
                    WHERE Title ILIKE %s OR Keywords ILIKE %s
                """, (f"%{search_query}%", f"%{search_query}%"))
                results = cursor.fetchall()
                cursor.close()
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
    document = None

    if conn:
        try:
            cursor = conn.cursor()
            # ✅ Fetch document details (Fixed query format)
            cursor.execute("SELECT Title, FilePath, Keywords, Summary FROM KnowledgeBase WHERE DocumentID = %s", (document_id,))
            document = cursor.fetchone()
            cursor.close()
        except Exception as e:
            flash(f"Error fetching document: {e}", "danger")
            return redirect(url_for('home'))
        finally:
            conn.close()

    # ✅ Prevent crash if document is not found
    if not document:
        flash("Document not found!", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # ✅ Get updated form data
        title = request.form.get('title')
        keywords = request.form.get('keywords')
        summary = request.form.get('summary')
        file = request.files['file']

        if not title:
            flash("Title is required!", "danger")
            return redirect(url_for('edit_document', document_id=document_id))

        # ✅ Save the new file if uploaded
        file_path = document[1]  # Preserve existing file path
        if file:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            file_path = os.path.relpath(file_path, start=os.getcwd())

        # ✅ Update the document in PostgreSQL
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE KnowledgeBase
                    SET Title = %s, FilePath = %s, Keywords = %s, Summary = %s, UploadDate = %s
                    WHERE DocumentID = %s
                """, (title, file_path, keywords, summary, datetime.datetime.now(), document_id))
                conn.commit()
                cursor.close()
                flash("Document updated successfully!", "success")
            except Exception as e:
                flash(f"Error updating document: {e}", "danger")
            finally:
                conn.close()

        return redirect(url_for('home'))

    return render_template('edit_document.html', document=document)


if __name__ == '__main__':
    app.run(debug=True)
