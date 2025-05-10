from flask import Flask, request, jsonify
import psycopg2
from dotenv import load_dotenv
import os
import psycopg2.extras
from psycopg2.extras import execute_values
from datetime import timezone, datetime, timedelta, date
from functools import wraps # Import wraps for the decorator
from werkzeug.security import generate_password_hash, check_password_hash # Import these
import jwt # Import PyJWT
import secrets
from flask_cors import CORS
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, DecodeError # *** Import specific exception classes ***
from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import text


load_dotenv()  # Load environment variables from .env file
app = Flask(__name__)
CORS(app)


SECRET_KEY = os.environ.get('SECRET_KEY', '@CyberBles0987654321')
app.config['SECRET_KEY'] = SECRET_KEY # Optional: add to Flask config


# # Database connection details (using environment variables for security)
print(f"DB_PORT from env: {os.getenv('DB_PORT')}")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")


database_url = os.environ.get('DATABASE_URL')

if database_url:
    # If DATABASE_URL is set, use it for SQLAlchemy
    # We replace 'postgresql://' with 'postgresql+psycopg2://' to tell SQLAlchemy
    # to use the psycopg2 driver. Ensure psycopg2-binary is installed (pip install psycopg2-binary).
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgresql://', 'postgresql+psycopg2://')
    print("Using DATABASE_URL for SQLAlchemy configuration.") # For debugging

else:
    # Fallback for local development if DATABASE_URL is NOT set
    # We read the individual local DB variables from the environment (loaded by load_dotenv)
    local_db_user = os.getenv("DB_USER")
    local_db_pass = os.getenv("DB_PASS")
    local_db_host = os.getenv("DB_HOST")
    local_db_port = os.getenv("DB_PORT") # This will be a string
    local_db_name = os.getenv("DB_NAME")

    # Construct the SQLAlchemy URI using the local variables
    # We also include the driver +psycopg2 here
    if local_db_user and local_db_pass and local_db_host and local_db_port and local_db_name:
         app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql+psycopg2://{local_db_user}:{local_db_pass}@{local_db_host}:{local_db_port}/{local_db_name}"
         print("DATABASE_URL not set, using local DB configuration from .env.") # For debugging
    else:
         # If neither DATABASE_URL nor local DB variables are fully set
         print("WARNING: DATABASE_URL not set and local DB config missing. Database features may not work.")
         # Set URI to None or a dummy value - SQLAlchemy will raise an error if you try to use db without a valid URI
         app.config['SQLALCHEMY_DATABASE_URI'] = None



db = SQLAlchemy(app)


# # New way (using DATABASE_URL)
# database_url = os.environ.get('DATABASE_URL')

# if database_url:
#     # SQLAlchemy often expects 'postgresql+drivername://' for some drivers like psycopg2
#     # So you might need to replace 'postgresql://'
#     app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgresql://', 'postgresql+psycopg2://')
# else:
#     # Fallback for local development (optional, you can remove or adjust)
#     app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://your_local_user:your_local_pass@localhost:5432/your_local_db" # Or whatever your local setup is


# # db = SQLAlchemy(app) # Initialize SQLAlchemy after config


######################################################################################################################################################

# --- Students and Lecturers Registration, Approval, and Rejection route ---
# The route which take care of students Reg. applications and sends infos to DB
@app.route('/register/student', methods=['POST'])
def register_student():
    if request.is_json:
        data = request.get_json()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        contact_number = data.get('contact_number')
        date_of_birth = data.get('date_of_birth')
        gender = data.get('gender')
        level = data.get('level')
        intended_department_name = data.get('intended_department_name')
        intended_program = data.get('intended_program')
        proposed_password = data.get('proposed_password')
        proposed_username = data.get('proposed_username')

        conn = None
        try:
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
            cur = conn.cursor()
            sql = "INSERT INTO AdmissionApplications (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_department_name, intended_program, proposed_password, proposed_username) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"
            values = (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_department_name, intended_program, proposed_password, proposed_username)
            
            cur.execute(sql, values)
            conn.commit()
            cur.close()
            return jsonify({"message": "Student registration successful!"}), 201  # 201 Created

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            return jsonify({"error": f"Database error: {e}"}), 500  # 500 Internal Server Error
        finally:
            if conn:
                conn.close()
    else:
        return jsonify({"error": "Request must be JSON"}), 400  # 400 Bad Request

# The route which take care of lecturers Reg. applications and sends infos to DB
@app.route('/register/lecturer', methods=['POST'])
def register_lecturer():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Extract lecturer details from the request
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    contact_number = data.get('contact_number')
    # Date of birth might be relevant for lecturers too
    date_of_birth = data.get('date_of_birth')
    gender = data.get('gender')
    # Level will indicate this is a lecturer application
    level = 'Lecturer Applicant' # Setting a default value for lecturers
    # Department they are applying to
    intended_department_name = data.get('intended_department_name')
    # Area of specialization or courses they can teach
    intended_program = data.get('intended_program') # Re-purposing this for lecturer
    proposed_password = data.get('proposed_password')
    proposed_username = data.get('proposed_username')

    # Add validation for required lecturer fields (adjust as needed)
    if not all([first_name, last_name, email, contact_number, intended_department_name, intended_program, proposed_password, proposed_username]):
        return jsonify({"error": "Missing required lecturer information."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Insert the lecturer application data into the AdmissionApplications table
        # Make sure the column names match your table exactly
        cur.execute(
            "INSERT INTO AdmissionApplications (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_department_name, intended_program, proposed_password, proposed_username, application_status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
            (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_department_name, intended_program, proposed_password, proposed_username, 'pending')
        )

        conn.commit()
        cur.close()
        return jsonify({"message": "Lecturer application submitted successfully!"}), 201 # 201 Created

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# The route that shows admins the pending applications for 'em to decide wether to approve or reject application
@app.route('/admin/applications', methods=['GET'])
def get_all_applications():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        cur.execute("SELECT * FROM AdmissionApplications;")
        applications = cur.fetchall()

        # Get column names for better formatting
        column_names = [desc[0] for desc in cur.description]

        # Convert list of tuples to list of dictionaries
        applications_list = []
        for row in applications:
            application = {}
            for i, column in enumerate(column_names):
                application[column] = row[i]
            applications_list.append(application)

        cur.close()
        return jsonify(applications_list), 200  # 200 OK

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/applications/<application_id>', methods=['PUT'])
def update_applicationstatus(application_id):
    """Updates the status of a student application."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    matriculation_number = data.get('matriculation_number')
    rejection_reason = data.get('rejection_reason')
    department_id_req = data.get('department_id')
    academic_year_id = data.get('academic_year_id')
    employee_id = data.get('employee_id')
    admin_id = data.get('admin_id')

    is_student_approval_data = all([matriculation_number, department_id_req, academic_year_id])
    is_lecturer_approval_data = all([employee_id, department_id_req])
    is_rejection_data = rejection_reason is not None

    if (is_student_approval_data and (is_lecturer_approval_data or is_rejection_data)) or \
       (is_lecturer_approval_data and (is_student_approval_data or is_rejection_data)) or \
       (is_rejection_data and (is_student_approval_data or is_lecturer_approval_data)):
         return jsonify({"error": "Provide data for only one action: student approval, lecturer approval, or rejection."}), 400


    if not admin_id:
        return jsonify({"error": "Admin ID is required for all actions."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        cur.execute("SELECT application_id, level, proposed_username, proposed_password, first_name, last_name, email, contact_number, date_of_birth, gender, intended_department_name, intended_program FROM AdmissionApplications WHERE application_id = %s;", (application_id,))
        application_details = cur.fetchone()

        if not application_details:
             return jsonify({"error": f"Application with ID {application_id} not found."}), 404

        app_id, level, proposed_username, proposed_password, first_name, last_name, email, contact_number, date_of_birth, gender, department_name_app, program_app = application_details

        cur.execute("SELECT application_status FROM AdmissionApplications WHERE application_id = %s;", (application_id,))
        current_app_status_row = cur.fetchone()
        current_app_status = current_app_status_row[0] if current_app_status_row else None

        new_status = data.get('status')

        if new_status == current_app_status:
             return jsonify({"message": f"Application status is already '{current_app_status}'."}), 200

        if current_app_status in ['approved', 'rejected']:
             return jsonify({"error": f"Application status is already '{current_app_status}' and cannot be changed."}), 400


        if new_status == 'approved' and is_student_approval_data:
            # --- Student Approval Logic ---

            if level not in ['Undergraduate', 'Graduate', '100', '200', '300', '400', '500']:
                 return jsonify({"error": f"Application with level '{level}' cannot be approved as a student."}), 400

            cur.execute("SELECT department_id FROM departments WHERE department_name = %s;", (department_name_app,))
            dept_row = cur.fetchone()
            if not dept_row:
                return jsonify({"error": f"Department '{department_name_app}' from application not found in departments table. Cannot approve."}), 400
            actual_department_id = dept_row[0]


            # Insert into students table
            insert_student_sql = """
                INSERT INTO students (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_program, department_id, matriculation_number, academic_year_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING student_id;
            """
            cur.execute(insert_student_sql, (
                first_name, last_name, email, contact_number, date_of_birth, gender, level, program_app, actual_department_id, matriculation_number, academic_year_id,
            ))
            new_student_id = cur.fetchone()[0]

            # --- Hash the password before storing ---
            hashed_password = generate_password_hash(proposed_password) # *** HASHING ***

            # Create user account for student - Insert HASHED password
            insert_user_sql = """
                 INSERT INTO useraccounts (username, password, role, entity_id)
                 VALUES (%s, %s, %s, %s)
                 RETURNING user_account_id;
             """
            cur.execute(insert_user_sql,
                 (proposed_username, hashed_password, 'student', new_student_id) # *** Use hashed_password ***
             )
            user_account_id = cur.fetchone()[0]


            # Now update the students table with the generated user_account_id
            update_student_user_account_sql = "UPDATE students SET user_account_id = %s WHERE student_id = %s;"
            cur.execute(update_student_user_account_sql, (user_account_id, new_student_id))


            # --- Generate and Update QR Code Data String ---
            qr_data_string = generate_student_qr_data_string(cur, new_student_id)
            if qr_data_string:
                update_qr_sql = "UPDATE students SET qr_code_data = %s WHERE student_id = %s;"
                cur.execute(update_qr_sql, (qr_data_string, new_student_id))
            else:
                 print(f"Warning: qr_data_string is None. Could not generate QR data string for new student_id {new_student_id}. qr_code_data column will be NULL.")


            # Insert/Update admissionstatus for student
            cur.execute(
                "INSERT INTO admissionstatus (application_id, status, approved_entity_id, approved_entity_type, approval_date, approved_by_admin_id) VALUES (%s, %s, %s, %s, NOW(), %s) ON CONFLICT (application_id) DO UPDATE SET status = %s, approved_entity_id = %s, approved_entity_type = %s, approval_date = NOW(), approved_by_admin_id = %s;",
                (application_id, 'approved', new_student_id, 'student', admin_id, 'approved', new_student_id, 'student', admin_id)
            )

            # Update AdmissionApplications table for student
            cur.execute(
                 "UPDATE AdmissionApplications SET application_status = 'approved' WHERE application_id = %s;",
                 (application_id,)
             )

            conn.commit()
            return jsonify({"message": f"Student application {application_id} approved with matriculation number {matriculation_number} by admin {admin_id}. Student added to students table with user account {proposed_username} (ID: {user_account_id}). Entity ID {new_student_id} linked."}), 200


        # elif new_status == 'approved' and is_lecturer_approval_data:
        #      # --- Lecturer Approval Logic ---
        #      if level != 'Lecturer Applicant':
        #           return jsonify({"error": f"Application with level '{level}' cannot be approved as a lecturer."}), 400

        #      cur.execute("SELECT department_id FROM departments WHERE department_name = %s;", (department_name_app,))
        #      dept_row = cur.fetchone()
        #      if not dept_row:
        #          return jsonify({"error": f"Department '{department_name_app}' from application not found in departments table. Cannot approve lecturer."}), 400
        #      actual_department_id = dept_row[0]

        #      # Insert into lecturers table
        #      insert_lecturer_sql = """
        #          INSERT INTO lecturers (first_name, last_name, email, contact_number, employee_id, department_id, user_account_id, date_of_employment)
        #          VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        #          RETURNING employee_id;
        #      """
        #      cur.execute(insert_lecturer_sql,
        #          (first_name, last_name, email, contact_number, employee_id, actual_department_id, None)
        #      )
        #      new_lecturer_id = cur.fetchone()[0]

        #      # --- Hash the password before storing ---
        #      hashed_password = generate_password_hash(proposed_password) # *** HASHING ***

        #      # Create user account for lecturer - Insert HASHED password
        #      insert_user_sql = """
        #           INSERT INTO useraccounts (username, password, role, entity_id)
        #           VALUES (%s, %s, %s, %s)
        #           RETURNING user_account_id;
        #       """
        #      cur.execute(insert_user_sql,
        #           (proposed_username, hashed_password, 'lecturer', new_lecturer_id) # *** Use hashed_password ***
        #       )
        #      user_account_id = cur.fetchone()[0]

        #      # Now update the lecturers table with the generated user_account_id
        #      update_lecturer_user_account_sql = "UPDATE lecturers SET user_account_id = %s WHERE employee_id = %s;"
        #      cur.execute(update_lecturer_user_account_sql, (user_account_id, new_lecturer_id))


        #      # Insert/Update admissionstatus for lecturer
        #      cur.execute(
        #          "INSERT INTO admissionstatus (application_id, status, approved_entity_id, approved_entity_type, approval_date, approved_by_admin_id) VALUES (%s, %s, %s, %s, NOW(), %s) ON CONFLICT (application_id) DO UPDATE SET status = %s, approved_entity_id = %s, approved_entity_type = %s, approval_date = NOW(), approved_by_admin_id = %s;",
        #          (application_id, 'approved', new_lecturer_id, 'lecturer', admin_id, 'approved', new_lecturer_id, 'lecturer', admin_id)
        #      )

        #      # Update AdmissionApplications table for lecturer
        #      cur.execute(
        #           "UPDATE AdmissionApplications SET application_status = 'approved' WHERE application_id = %s;",
        #           (application_id,)
        #       )

        #      conn.commit()
        #      return jsonify({"message": f"Lecturer application {application_id} approved with employee ID {employee_id} by admin {admin_id}. Lecturer added to lecturers table with user account {proposed_username} (ID: {user_account_id}). Entity ID {new_lecturer_id} linked."}), 200

        # elif new_status == 'approved' and is_lecturer_approval_data:
        #      # --- Lecturer Approval Logic ---
        #      if level != 'Lecturer Applicant':
        #           return jsonify({"error": f"Application with level '{level}' cannot be approved as a lecturer."}), 400

        #      cur.execute("SELECT department_id FROM departments WHERE department_name = %s;", (department_name_app,))
        #      dept_row = cur.fetchone()
        #      if not dept_row:
        #          return jsonify({"error": f"Department '{department_name_app}' from application not found in departments table. Cannot approve lecturer."}), 400
        #      actual_department_id = dept_row[0]

        #      # Insert into lecturers table - *** CORRECTED: REMOVED user_account_id from INSERT ***
        #      # Assuming employee_id is the primary key and is provided in the request
        #      insert_lecturer_sql = """
        #          INSERT INTO lecturers (first_name, last_name, email, contact_number, employee_id, department_id, date_of_employment)
        #          VALUES (%s, %s, %s, %s, %s, %s, NOW()) -- *** CORRECTED: 6 placeholders + NOW() ***
        #          RETURNING employee_id; -- Assuming employee_id is PK and you want it back
        #      """
        #      cur.execute(insert_lecturer_sql,
        #          (first_name, last_name, email, contact_number, employee_id, actual_department_id) # *** CORRECTED: 6 values matching columns ***
        #          # *** CORRECTED: Removed the None placeholder for user_account_id ***
        #      )
        #      new_lecturer_id = cur.fetchone()[0] # Capture the newly created lecturer_id (employee_id)


        #      # --- Hash the password before storing ---
        #      hashed_password = generate_password_hash(proposed_password)

        #      # Create user account for lecturer - Insert HASHED password and entity_id
        #      insert_user_sql = """
        #           INSERT INTO useraccounts (username, password, role, entity_id)
        #           VALUES (%s, %s, %s, %s)
        #           RETURNING user_account_id;
        #       """
        #      cur.execute(insert_user_sql,
        #           (proposed_username, hashed_password, 'lecturer', new_lecturer_id) # Pass new_lecturer_id as entity_id
        #       )
        #      user_account_id = cur.fetchone()[0]

        #      # Now update the lecturers table with the generated user_account_id
        #      update_lecturer_user_account_sql = "UPDATE lecturers SET user_account_id = %s WHERE employee_id = %s;"
        #      cur.execute(update_lecturer_user_account_sql, (user_account_id, new_lecturer_id))


        #      # Insert/Update admissionstatus for lecturer
        #      cur.execute(
        #          "INSERT INTO admissionstatus (application_id, status, approved_entity_id, approved_entity_type, approval_date, approved_by_admin_id) VALUES (%s, %s, %s, %s, NOW(), %s) ON CONFLICT (application_id) DO UPDATE SET status = %s, approved_entity_id = %s, approved_entity_type = %s, approval_date = NOW(), approved_by_admin_id = %s;",
        #          (application_id, 'approved', new_lecturer_id, 'lecturer', admin_id, 'approved', new_lecturer_id, 'lecturer', admin_id)
        #      )

        #      # Update AdmissionApplications table for lecturer
        #      cur.execute(
        #           "UPDATE AdmissionApplications SET application_status = 'approved' WHERE application_id = %s;",
        #           (application_id,)
        #       )

        #      conn.commit()
        #      return jsonify({"message": f"Lecturer application {application_id} approved with employee ID {employee_id} by admin {admin_id}. Lecturer added to lecturers table with user account {proposed_username} (ID: {user_account_id}). Entity ID {new_lecturer_id} linked."}), 200


        elif new_status == 'approved' and is_lecturer_approval_data:
             # --- Lecturer Approval Logic ---
             if level != 'Lecturer Applicant':
                  return jsonify({"error": f"Application with level '{level}' cannot be approved as a lecturer."}), 400

             cur.execute("SELECT department_id FROM departments WHERE department_name = %s;", (department_name_app,))
             dept_row = cur.fetchone()
             if not dept_row:
                 return jsonify({"error": f"Department '{department_name_app}' from application not found in departments table. Cannot approve lecturer."}), 400
             actual_department_id = dept_row[0]

             # Insert into lecturers table - *** MODIFIED: RETURNING lecturer_id ***
             # Assuming lecturer_id is the primary key generated by the database
             insert_lecturer_sql = """
                 INSERT INTO lecturers (first_name, last_name, email, contact_number, employee_id, department_id, date_of_employment)
                 VALUES (%s, %s, %s, %s, %s, %s, NOW())
                 RETURNING lecturer_id; -- *** MODIFIED: Return the PK (lecturer_id) ***
             """
             # Note: employee_id is still provided here as it's likely data from the application/request
             cur.execute(insert_lecturer_sql,
                 (first_name, last_name, email, contact_number, employee_id, actual_department_id)
             )
             new_lecturer_pk_id = cur.fetchone()[0] # *** MODIFIED: Capture the returned lecturer_id ***


             # --- Hash the password before storing ---
             hashed_password = generate_password_hash(proposed_password)

             # Create user account for lecturer - Insert HASHED password and ***lecturer_id*** as entity_id
             insert_user_sql = """
                  INSERT INTO useraccounts (username, password, role, entity_id)
                  VALUES (%s, %s, %s, %s)
                  RETURNING user_account_id;
              """
             cur.execute(insert_user_sql,
                  (proposed_username, hashed_password, 'lecturer', new_lecturer_pk_id) # *** MODIFIED: Pass the captured lecturer_id as entity_id ***
              )
             user_account_id = cur.fetchone()[0]

             # Now update the lecturers table with the generated user_account_id - *** MODIFIED: Use lecturer_id in WHERE ***
             update_lecturer_user_account_sql = "UPDATE lecturers SET user_account_id = %s WHERE lecturer_id = %s;"
             cur.execute(update_lecturer_user_account_sql, (user_account_id, new_lecturer_pk_id)) # *** MODIFIED: Use lecturer_id in WHERE ***


             # Insert/Update admissionstatus for lecturer - *** MODIFIED: Use lecturer_id as approved_entity_id ***
             cur.execute(
                 "INSERT INTO admissionstatus (application_id, status, approved_entity_id, approved_entity_type, approval_date, approved_by_admin_id) VALUES (%s, %s, %s, %s, NOW(), %s) ON CONFLICT (application_id) DO UPDATE SET status = %s, approved_entity_id = %s, approved_entity_type = %s, approval_date = NOW(), approved_by_admin_id = %s;",
                 (application_id, 'approved', new_lecturer_pk_id, 'lecturer', admin_id, 'approved', new_lecturer_pk_id, 'lecturer', admin_id) # *** MODIFIED: Use lecturer_id for approved_entity_id ***
             )

             # Update AdmissionApplications table for lecturer
             cur.execute(
                  "UPDATE AdmissionApplications SET application_status = 'approved' WHERE application_id = %s;",
                  (application_id,)
              )

             conn.commit()
             return jsonify({"message": f"Lecturer application {application_id} approved with employee ID {employee_id} by admin {admin_id}. Lecturer added to lecturers table with user account {proposed_username} (ID: {user_account_id}). Entity ID (lecturer_id) {new_lecturer_pk_id} linked."}), 200 # Added detail to message

        elif new_status == 'rejected' and is_rejection_data:
            # --- Rejection Logic ---
            cur.execute(
                "INSERT INTO admissionstatus (application_id, status, rejection_reason, rejection_date, approved_by_admin_id, approved_entity_id, approved_entity_type) VALUES (%s, %s, %s, NOW(), %s, NULL, NULL) ON CONFLICT (application_id) DO UPDATE SET status = %s, rejection_reason = %s, rejection_date = NOW(), approved_by_admin_id = %s, approved_entity_id = NULL, approved_entity_type = NULL;",
                (application_id, 'rejected', rejection_reason, admin_id, 'rejected', rejection_reason, admin_id)
            )

            cur.execute(
                 "UPDATE AdmissionApplications SET application_status = 'rejected' WHERE application_id = %s;",
                 (application_id,)
             )

            conn.commit()
            return jsonify({"message": f"Application {application_id} rejected with reason: {rejection_reason} by admin {admin_id}."}), 200

        else:
             return jsonify({"error": "Invalid status update or missing required data for the specified status."}), 400


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during application update: {e}")
        return jsonify({"error": f"Database integrity error: {e}"}), 409

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during application update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during application update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# The Python function that pull out student details and genrate QR Code for them  
def generate_student_qr_data_string(cur, student_id):
    """
    Fetches student details using an existing cursor and formats them into a string.
    Returns the formatted string or None if student is not found or error occurs.
    Accepts:
        cur: An active database cursor (must use RealDictCursor or adapt logic)
        student_id: The ID of the student (VARCHAR)
    """
    # --- DEBUG PRINT STATEMENTS ADDED ---
    print(f"--- generate_student_qr_data_string called for student_id: {student_id} ---")
    # Removed connection/cursor setup

    qr_data_string = None

    try:
        # Ensure the cursor is a RealDictCursor for dictionary access, or adapt logic
        if not isinstance(cur, psycopg2.extras.RealDictCursor):
             # Create a new RealDictCursor from the same connection if the passed one is not
             # This might be slightly less efficient but safer if different cursor types are used
             # Alternatively, require the caller to pass a RealDictCursor
             print("Warning: generate_student_qr_data_string received non-RealDictCursor, creating a new one.")
             dict_cur = cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
             dict_cur = cur # Use the passed cursor

        sql = """
            SELECT
                s.student_id,
                s.first_name,
                s.last_name,
                s.matriculation_number,
                s.level,
                d.department_name
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            WHERE s.student_id = %s;
        """
        print(f"Executing SQL in QR function: {sql} with student_id: {student_id}")
        dict_cur.execute(sql, (str(student_id),))

        student_details = dict_cur.fetchone()

        # Do NOT close cursor or connection here! The caller manages them.
        # if not isinstance(cur, psycopg2.extras.RealDictCursor):
        #     dict_cur.close() # Close the temporary cursor if created


        if student_details:
            print(f"Fetched student details: {student_details}")
            qr_data_string = (
                f"ID:{student_details['student_id']},"
                f"Name:{student_details['first_name']} {student_details['last_name']},"
                f"Matric:{student_details['matriculation_number']},"
                f"Level:{student_details['level']},"
                f"Dept:{student_details['department_name']}"
            )
            print(f"Generated QR data string: {qr_data_string}")
        else:
            print(f"No student details found for student_id: {student_id}")

    except psycopg2.Error as e:
        print(f"Database error fetching student details for QR code: {e}")
        qr_data_string = None
    except Exception as e:
        print(f"An unexpected error occurred fetching student details for QR code: {e}")
        qr_data_string = None

    # Removed finally block for closing connection/cursor

    print(f"--- generate_student_qr_data_string returning: {qr_data_string} ---")
    return qr_data_string
# --- Students and Lecturers Registration, Approval, and Rejection route ---

######################################################################################################################################################

# --- Course Management Routes ---
@app.route('/courses', methods=['POST'])
def create_course():
    """Creates a new course."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Extract course details from the request
    course_title = data.get('course_title')
    course_code = data.get('course_code')
    description = data.get('description')
    department_id = data.get('department_id') # FK to departments
    credits = data.get('credits')
    level = data.get('level') # Optional based on schema

    # Validate required fields
    if not all([course_title, course_code, department_id, credits is not None]):
        return jsonify({"error": "Missing required course information (course_title, course_code, department_id, credits)."}), 400

    # Validate credits type
    if not isinstance(credits, int) or credits < 0:
         return jsonify({"error": "Credits must be a non-negative integer."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Insert the new course into the courses table
        # course_id is SERIAL/generated by trigger, so we don't include it in INSERT
        # department_id is VARCHAR(10) in courses table per schema
        # level is VARCHAR(5) and nullable
        cur.execute(
            "INSERT INTO courses (course_title, course_code, description, department_id, credits, level) VALUES (%s, %s, %s, %s, %s, %s) RETURNING course_id;",
            (course_title, course_code, description, str(department_id), credits, level)
        )
        new_course_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": "Course created successfully!", "course_id": new_course_id}), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        # Handle unique constraint violation (course_code) or foreign key violation (department_id)
        if 'unique constraint "courses_course_code_key"' in str(e):
             return jsonify({"error": "Course code already exists."}), 409 # Conflict
        elif 'foreign key constraint "courses_department_id_fkey"' in str(e):
             return jsonify({"error": f"Department ID '{department_id}' does not exist."}), 409 # Conflict
        else:
             return jsonify({"error": f"Database integrity error: {e}"}), 500
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/courses', methods=['GET'])
def get_all_courses():
    """Retrieves all courses or filters by name."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        course_title_filter = request.args.get('name') # Get the 'name' query parameter

        if course_title_filter:
            # If 'name' parameter is present, filter by course_title (case-insensitive like)
            # Using ILIKE for case-insensitive matching in PostgreSQL
            sql = "SELECT * FROM courses WHERE course_title ILIKE %s;"
            # Add wildcards for partial matching (e.g., allows searching for 'Intro' to find 'Introduction to...')
            cur.execute(sql, ('%' + course_title_filter + '%',))
        else:
            # If no 'name' parameter, get all courses
            sql = "SELECT * FROM courses;"
            cur.execute(sql)

        courses = cur.fetchall()

        return jsonify(courses), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/courses/<course_id>', methods=['GET'])
def get_course_by_id(course_id):
    """Retrieves a single course by its ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        cur.execute("SELECT * FROM courses WHERE course_id = %s;", (course_id,))
        course = cur.fetchone()

        if course is None:
            return jsonify({"error": f"Course with ID '{course_id}' not found."}), 404

        return jsonify(course), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/courses/<course_id>', methods=['PUT'])
def update_course(course_id):
    """Updates an existing course."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    # Get fields to update - only include fields present in the request body
    update_fields = {}
    allowed_fields = ['course_title', 'course_code', 'description', 'department_id', 'credits', 'level']

    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]

    if not update_fields:
        return jsonify({"error": "No update fields provided."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Check if the course exists
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (course_id,))
        course_exists = cur.fetchone()
        if not course_exists:
            return jsonify({"error": f"Course with ID '{course_id}' not found."}), 404

        # Build the UPDATE query dynamically based on provided fields
        set_clauses = []
        values = []
        for field, value in update_fields.items():
             set_clauses.append(f"{field} = %s")
             if field in ['department_id']: # Cast specific fields to string if needed
                 values.append(str(value))
             else:
                values.append(value)

        sql = f"UPDATE courses SET {', '.join(set_clauses)} WHERE course_id = %s;"
        values.append(course_id) # Add course_id for the WHERE clause

        cur.execute(sql, tuple(values))

        conn.commit()
        # Check if any row was actually updated
        if cur.rowcount == 0:
             return jsonify({"message": f"Course with ID '{course_id}' found, but no changes were made (data was the same)."}), 200
        else:
             return jsonify({"message": f"Course with ID '{course_id}' updated successfully."}), 200

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        # Handle unique constraint violation (course_code) or foreign key violation (department_id)
        if 'unique constraint "courses_course_code_key"' in str(e):
             return jsonify({"error": "Course code already exists."}), 409 # Conflict
        elif 'foreign key constraint "courses_department_id_fkey"' in str(e):
             # Extract the department_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(department_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Department ID '{fk_value or 'department_id_req'}' does not exist."}), 409 # Conflict
        else:
             return jsonify({"error": f"Database integrity error: {e}"}), 500

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/courses/<course_id>', methods=['DELETE'])
def delete_course(course_id):
    """Deletes a course by its ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Delete the course
        cur.execute("DELETE FROM courses WHERE course_id = %s;", (course_id,))

        conn.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            return jsonify({"error": f"Course with ID '{course_id}' not found."}), 404
        else:
            return jsonify({"message": f"Course with ID '{course_id}' deleted successfully."}), 200

    except psycopg2.IntegrityError as e:
         if conn:
             conn.rollback()
         # Handle foreign key violation if other tables (like attendance_sessions) reference this course
         return jsonify({"error": f"Cannot delete course '{course_id}' because other records (e.g., attendance sessions) depend on it. Error: {e}"}), 409 # Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
# --- Course Management Routes Ends Here---

######################################################################################################################################################

# --- Lecturer Course Assignment Routes ---
# The route that allow an admin (or authorized user) to assign a lecturer to a specific course for a specific academic year.
@app.route('/assignments/lecturer', methods=['POST'])
def assign_lecturer_to_course():
    """Assigns a lecturer to teach a course for a specific academic year."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Extract assignment details from the request
    lecturer_id = data.get('lecturer_id')
    course_id = data.get('course_id')
    academic_year_id = data.get('academic_year_id')
    role = data.get('role') # Optional

    # Validate required fields
    if not all([lecturer_id, course_id, academic_year_id]):
        return jsonify({"error": "Missing required assignment information (lecturer_id, course_id, academic_year_id)."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Insert the new assignment into the coursesassignedtolecturers table
        # assignment_id is generated by the trigger, so we don't include it in INSERT
        # Ensure data types match the table (VARCHAR for IDs)
        cur.execute(
            "INSERT INTO coursesassignedtolecturers (lecturer_id, course_id, academic_year_id, role) VALUES (%s, %s, %s, %s) RETURNING assignment_id;",
            (str(lecturer_id), str(course_id), str(academic_year_id), role)
        )
        new_assignment_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": "Lecturer assigned to course successfully!", "assignment_id": new_assignment_id}), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        # Handle unique constraint violation (same lecturer, course, year) or foreign key violations
        if 'unique constraint "coursesassignedtolecturers_lecturer_id_course_id_academi_key"' in str(e) or \
           'duplicate key value violates unique constraint "coursesassignedtolecturers_lecturer_id_course_id_academi_key"' in str(e):
             return jsonify({"error": "This lecturer is already assigned to this course for this academic year."}), 409 # Conflict
        elif 'foreign key constraint "coursesassignedtolecturers_lecturer_id_fkey"' in str(e):
             # Extract the lecturer_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(lecturer_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Lecturer ID '{fk_value or lecturer_id}' does not exist."}), 409 # Conflict
        elif 'foreign key constraint "coursesassignedtolecturers_course_id_fkey"' in str(e):
             # Extract the course_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(course_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Course ID '{fk_value or course_id}' does not exist."}), 409 # Conflict
        elif 'foreign key constraint "coursesassignedtolecturers_academic_year_id_fkey"' in str(e):
             # Extract the academic_year_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(academic_year_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Academic Year ID '{fk_value or academic_year_id}' does not exist."}), 409 # Conflict
        else:
             return jsonify({"error": f"Database integrity error: {e}"}), 500
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/assignments/lecturer', methods=['GET'])
def get_lecturer_assignments():
    """Retrieves all lecturer assignments, with optional filtering by lecturer, course, or academic year."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Get optional query parameters for filtering
        lecturer_id_filter = request.args.get('lecturer_id')
        course_id_filter = request.args.get('course_id')
        academic_year_id_filter = request.args.get('academic_year_id')

        sql = "SELECT * FROM coursesassignedtolecturers"
        conditions = []
        values = []

        if lecturer_id_filter:
            conditions.append("lecturer_id = %s")
            values.append(str(lecturer_id_filter)) # Cast to string for VARCHAR column
        if course_id_filter:
            conditions.append("course_id = %s")
            values.append(str(course_id_filter))   # Cast to string for VARCHAR column
        if academic_year_id_filter:
            conditions.append("academic_year_id = %s")
            values.append(str(academic_year_id_filter)) # Cast to string for VARCHAR column

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # Optional: Add ORDER BY for consistent results
        sql += " ORDER BY academic_year_id, lecturer_id, course_id;"

        cur.execute(sql, tuple(values))

        assignments = cur.fetchall()

        return jsonify(assignments), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/assignments/lecturer/<assignment_id>', methods=['GET'])
def get_lecturer_assignment_by_id(assignment_id):
    """Retrieves a single lecturer assignment by its assignment ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # assignment_id is VARCHAR, so cast the URL parameter to string if it's not already
        cur.execute("SELECT * FROM coursesassignedtolecturers WHERE assignment_id = %s;", (str(assignment_id),))

        assignment = cur.fetchone()

        if assignment is None:
            return jsonify({"error": f"Assignment with ID '{assignment_id}' not found."}), 404

        return jsonify(assignment), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/assignments/lecturer/<assignment_id>', methods=['DELETE'])
def delete_lecturer_assignment(assignment_id):
    """Deletes a lecturer assignment by its assignment ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Delete the assignment record
        # assignment_id is VARCHAR, so cast the URL parameter to string if it's not already
        cur.execute("DELETE FROM coursesassignedtolecturers WHERE assignment_id = %s;", (str(assignment_id),))

        conn.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            # If rowcount is 0, no record with that ID was found
            return jsonify({"error": f"Assignment with ID '{assignment_id}' not found."}), 404
        else:
            # If rowcount is > 0, the record was deleted
            return jsonify({"message": f"Assignment with ID '{assignment_id}' deleted successfully."}), 200

    except psycopg2.IntegrityError as e:
         if conn:
             conn.rollback()
         # Handle foreign key violation if other tables somehow reference this assignment_id
         return jsonify({"error": f"Cannot delete assignment '{assignment_id}' because other records depend on it. Error: {e}"}), 409 # Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
# --- Lecturer Course Assignment Routes Ends Here---

######################################################################################################################################################

# --- Student Enrollment to Courses Routes ---
@app.route('/enrollments/student', methods=['POST'])
def enroll_student_in_course():
    """Enrolls a student in a course for a specific academic year."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Extract enrollment details from the request
    student_id = data.get('student_id')
    course_id = data.get('course_id')
    academic_year_id = data.get('academic_year_id')
    status = data.get('status') # Optional, defaults to 'Enrolled' in DB

    # Validate required fields
    if not all([student_id, course_id, academic_year_id]):
        return jsonify({"error": "Missing required enrollment information (student_id, course_id, academic_year_id)."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Insert the new enrollment into the studentsenrolledcourses table
        # enrollment_id is generated by the trigger, so we don't include it in INSERT
        # Ensure data types match the table (VARCHAR for student_id, course_id, academic_year_id)
        cur.execute(
            "INSERT INTO studentsenrolledcourses (student_id, course_id, academic_year_id, status) VALUES (%s, %s, %s, %s) RETURNING enrollment_id;",
            (str(student_id), str(course_id), str(academic_year_id), status)
        )
        new_enrollment_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": "Student enrolled in course successfully!", "enrollment_id": new_enrollment_id}), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        # Handle unique constraint violation (same student, course, year) or foreign key violations
        if 'unique constraint "studentsenrolledcourses_student_id_course_id_academic_key"' in str(e) or \
           'duplicate key value violates unique constraint "studentsenrolledcourses_student_id_course_id_academic_key"' in str(e):
             return jsonify({"error": "This student is already enrolled in this course for this academic year."}), 409 # Conflict
        elif 'foreign key constraint "studentsenrolledcourses_student_id_fkey"' in str(e):
             # Extract the student_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(student_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Student ID '{fk_value or student_id}' does not exist."}), 409 # Conflict
        elif 'foreign key constraint "studentsenrolledcourses_course_id_fkey"' in str(e):
             # Extract the course_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(course_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Course ID '{fk_value or course_id}' does not exist."}), 409 # Conflict
        elif 'foreign key constraint "studentsenrolledcourses_academic_year_id_fkey"' in str(e):
             # Extract the academic_year_id value that caused the FK error for better message
             fk_value = None
             import re
             match = re.search(r'Key \(academic_year_id\)=\((.*?)\) is not present', str(e))
             if match:
                 fk_value = match.group(1)
             return jsonify({"error": f"Academic Year ID '{fk_value or academic_year_id}' does not exist."}), 409 # Conflict
        else:
             return jsonify({"error": f"Database integrity error: {e}"}), 500
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/enrollments/student', methods=['GET'])
def get_student_enrollments():
    """Retrieves all student enrollments, with optional filtering by student, course, or academic year."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Get optional query parameters for filtering
        student_id_filter = request.args.get('student_id')
        course_id_filter = request.args.get('course_id')
        academic_year_id_filter = request.args.get('academic_year_id')

        sql = "SELECT * FROM studentsenrolledcourses"
        conditions = []
        values = []

        if student_id_filter:
            conditions.append("student_id = %s")
            values.append(str(student_id_filter)) # Cast to string for VARCHAR column
        if course_id_filter:
            conditions.append("course_id = %s")
            values.append(str(course_id_filter))   # Cast to string for VARCHAR column
        if academic_year_id_filter:
            conditions.append("academic_year_id = %s")
            values.append(str(academic_year_id_filter)) # Cast to string for VARCHAR column

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # Optional: Add ORDER BY for consistent results
        sql += " ORDER BY academic_year_id, student_id, course_id;"


        cur.execute(sql, tuple(values))

        enrollments = cur.fetchall()

        return jsonify(enrollments), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/enrollments/student/<enrollment_id>', methods=['GET'])
def get_student_enrollment_by_id(enrollment_id):
    """Retrieves a single student enrollment by its enrollment ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # enrollment_id is VARCHAR, so cast the URL parameter to string if it's not already
        cur.execute("SELECT * FROM studentsenrolledcourses WHERE enrollment_id = %s;", (str(enrollment_id),))

        enrollment = cur.fetchone()

        if enrollment is None:
            return jsonify({"error": f"Enrollment with ID '{enrollment_id}' not found."}), 404

        return jsonify(enrollment), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/enrollments/student/<enrollment_id>', methods=['DELETE'])
def delete_student_enrollment(enrollment_id):
    """Deletes a student enrollment by its enrollment ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Delete the enrollment record
        # enrollment_id is VARCHAR, so cast the URL parameter to string if it's not already
        cur.execute("DELETE FROM studentsenrolledcourses WHERE enrollment_id = %s;", (str(enrollment_id),))

        conn.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            # If rowcount is 0, no record with that ID was found
            return jsonify({"error": f"Enrollment with ID '{enrollment_id}' not found."}), 404
        else:
            # If rowcount is > 0, the record was deleted
            return jsonify({"message": f"Enrollment with ID '{enrollment_id}' deleted successfully."}), 200

    except psycopg2.IntegrityError as e:
         if conn:
             conn.rollback()
         # Handle foreign key violation if other tables somehow reference this enrollment_id
         # This is less likely for a junction table's PK, but good practice to include
         return jsonify({"error": f"Cannot delete enrollment '{enrollment_id}' because other records depend on it. Error: {e}"}), 409 # Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
# --- Student Enrollment to Courses Routes Ends Here ---

######################################################################################################################################################

# --- Attendance Recording Route ---
@app.route('/attendance/record', methods=['POST'])
def record_attendance():
    """Records student attendance for a specific session based on scanned student ID."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Extract data from the request (simulating receiving session ID and scanned student ID)
    session_id = data.get('session_id')     # Identifier for the current session
    student_id_from_qr = data.get('student_id') # Student ID obtained from scanning the QR code

    # Validate required input
    if not all([session_id, student_id_from_qr]):
        return jsonify({"error": "Missing required information (session_id, student_id)."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # --- Validation: Check if session is valid and not expired ---
        cur.execute(
            "SELECT qr_code_expiry_time FROM attendancesessions WHERE session_id = %s;",
            (str(session_id),) # Cast to string for VARCHAR session_id
        )
        session_info = cur.fetchone()

        if session_info is None:
            return jsonify({"error": f"Attendance session with ID '{session_id}' not found."}), 404

        qr_expiry_time = session_info[0] # Get the expiry time

        # Get the current time (make it timezone aware if your DB timestamps are)
        # Assuming your DB stores TIMESTAMP WITH TIME ZONE and server is configured correctly
        current_time = datetime.now(timezone.utc) # Use timezone.utc if DB is UTC or adjust as needed

        # Compare current time with expiry time
        if current_time > qr_expiry_time:
             return jsonify({"error": f"Attendance window for session '{session_id}' has expired."}), 400


        # --- Validation: Check if student exists ---
        # Assuming your students table has a student_id column that is the PK or unique
        cur.execute(
            "SELECT student_id FROM students WHERE student_id = %s;",
            (str(student_id_from_qr),) # Cast to string for VARCHAR student_id
        )
        student_exists = cur.fetchone()

        if student_exists is None:
             return jsonify({"error": f"Student with ID '{student_id_from_qr}' not found."}), 404

        # --- Record Attendance ---
        # Insert into attendancerecords
        # record_id is generated by trigger, don't include it
        # session_id and student_id are VARCHAR, cast to string
        # attendance_time uses NOW()::TIMESTAMP WITH TIME ZONE to match column type
        cur.execute(
            "INSERT INTO attendancerecords (session_id, student_id, attendance_time, status) VALUES (%s, %s, NOW()::TIMESTAMP WITH TIME ZONE, %s) RETURNING record_id;",
            (str(session_id), str(student_id_from_qr), 'Present') # Default status to 'Present'
        )
        new_record_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": f"Attendance recorded for student '{student_id_from_qr}' in session '{session_id}'.", "record_id": new_record_id}), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        # Handle unique constraint violation (student already recorded for this session)
        if 'unique constraint "attendancerecords_session_id_student_id_key"' in str(e) or \
           'duplicate key value violates unique constraint "attendancerecords_session_id_student_id_key"' in str(e):
             return jsonify({"error": f"Attendance already recorded for student '{student_id_from_qr}' in session '{session_id}'."}), 409 # Conflict
        # Foreign key violations for session_id or student_id should ideally be caught by explicit checks above,
        # but including handling here as a fallback is safe.
        elif 'foreign key constraint "attendancerecords_session_id_fkey"' in str(e):
             return jsonify({"error": f"Database error: Invalid session ID '{session_id}' (FK constraint).", "detail": str(e)}), 409
        elif 'foreign key constraint "attendancerecords_student_id_fkey"' in str(e):
             return jsonify({"error": f"Database error: Invalid student ID '{student_id_from_qr}' (FK constraint).", "detail": str(e)}), 409
        else:
             return jsonify({"error": f"Database integrity error: {e}"}), 500
    except (psycopg2.Error, Exception) as e: # Catch other potential errors
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance recording: {e}") # Log the error
        return jsonify({"error": f"An error occurred: {e}"}), 500 # Generic error for client
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- Attendance Record Viewing Routes ---
@app.route('/attendance/records', methods=['GET'])
def get_attendance_records():
    """Retrieves all attendance records, with optional filtering by session or student."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Get optional query parameters for filtering
        session_id_filter = request.args.get('session_id')
        student_id_filter = request.args.get('student_id')
        status_filter = request.args.get('status')
        # You could add filtering by date range here as well if needed

        sql = "SELECT * FROM attendancerecords"
        conditions = []
        values = []

        if session_id_filter:
            conditions.append("session_id = %s")
            values.append(str(session_id_filter)) # Cast to string for VARCHAR column
        if student_id_filter:
            conditions.append("student_id = %s")
            values.append(str(student_id_filter))   # Cast to string for VARCHAR column
        if status_filter:
             conditions.append("status = %s")
             values.append(str(status_filter)) # Cast to string for VARCHAR column


        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # Optional: Add ORDER BY for consistent results
        sql += " ORDER BY attendance_time DESC;" # Order by most recent attendance first


        cur.execute(sql, tuple(values))

        records = cur.fetchall()

        return jsonify(records), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/attendance/records/<record_id>', methods=['GET'])
def get_attendance_record_by_id(record_id):
    """Retrieves a single attendance record by its record ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # record_id is VARCHAR, so cast the URL parameter to string
        cur.execute("SELECT * FROM attendancerecords WHERE record_id = %s;", (str(record_id),))

        record = cur.fetchone()

        if record is None:
            return jsonify({"error": f"Attendance record with ID '{record_id}' not found."}), 404

        return jsonify(record), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/attendance/records/<record_id>', methods=['DELETE'])
def delete_attendance_record(record_id):
    """Deletes an attendance record by its record ID."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Delete the attendance record
        # record_id is VARCHAR, so cast the URL parameter to string
        cur.execute("DELETE FROM attendancerecords WHERE record_id = %s;", (str(record_id),))

        conn.commit()

        # Check if any row was deleted
        if cur.rowcount == 0:
            # If rowcount is 0, no record with that ID was found
            return jsonify({"error": f"Attendance record with ID '{record_id}' not found."}), 404
        else:
            # If rowcount is > 0, the record was deleted
            return jsonify({"message": f"Attendance record with ID '{record_id}' deleted successfully."}), 200

    except psycopg2.IntegrityError as e:
         if conn:
             conn.rollback()
         # Handle foreign key violation if other tables somehow reference this record_id
         # This is very unlikely for attendance_records PK, but included for completeness
         return jsonify({"error": f"Cannot delete attendance record '{record_id}' because other records depend on it. Error: {e}"}), 409 # Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/sessions', methods=['GET'])
def get_attendance_sessions():
    """Retrieves all attendance sessions, with optional filtering."""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Get optional query parameters for filtering
        assignment_id_filter = request.args.get('assignment_id')
        start_date_filter = request.args.get('start_date') # e.g., YYYY-MM-DD
        end_date_filter = request.args.get('end_date')   # e.g., YYYY-MM-DD

        sql = "SELECT * FROM attendancesessions"
        conditions = []
        values = []

        if assignment_id_filter:
            conditions.append("assignment_id = %s")
            values.append(str(assignment_id_filter)) # Cast to string for VARCHAR column

        if start_date_filter:
            try:
                # Parse the date string and look for sessions >= start of this date
                datetime.fromisoformat(start_date_filter) # Basic validation
                conditions.append("session_datetime >= %s")
                values.append(f"{start_date_filter} 00:00:00") # Include time part for comparison
            except ValueError:
                 return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400

        if end_date_filter:
             try:
                 # Parse the date string and look for sessions < start of the *next* date
                 # This correctly includes sessions throughout the end_date
                 end_datetime = datetime.fromisoformat(end_date_filter) + timedelta(days=1)
                 conditions.append("session_datetime < %s")
                 values.append(end_datetime.strftime('%Y-%m-%d %H:%M:%S')) # Format for SQL
             except ValueError:
                  return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400


        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # Optional: Add ORDER BY for consistent results
        sql += " ORDER BY session_datetime DESC;" # Order by most recent sessions first


        cur.execute(sql, tuple(values))

        sessions = cur.fetchall()

        return jsonify(sessions), 200

    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
# --- Attendance Record Viewing Routes Ends Here ---
# --- All About Attendance recordning ---

######################################################################################################################################################

#--- Authentication Route for Users Logins---
@app.route('/login', methods=['POST'])
def login_user():
    """Authenticates a user based on username and password, returns a JWT."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "Missing username or password."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Select the stored HASHED password, user_account_id, role, and entity_id
        cur.execute(
            "SELECT user_account_id, password, role, entity_id FROM useraccounts WHERE username = %s;",
            (username,)
        )
        user_account = cur.fetchone()

        if user_account is None:
            # User not found
            return jsonify({"error": "Invalid username or password."}), 401 # 401 Unauthorized

        user_account_id, stored_password_hash, role, entity_id = user_account

        # --- Password Verification ---
        if check_password_hash(stored_password_hash, password):
            # Authentication successful - *** GENERATE JWT ***

            # Define the payload (claims) for the token.
            # Include data needed for authentication/authorization checks later.
            # Standard claims like 'exp' (expiration) are important in production.
            payload = {
                'user_account_id': user_account_id,
                'role': role,
                'entity_id': entity_id
                # 'exp': datetime.utcnow() + timedelta(minutes=30) # Example expiration (requires import)
            }

            # Encode the payload into a JWT using the secret key
            # Algorithm 'HS256' is HMAC with SHA-256
            token = jwt.encode(payload, SECRET_KEY, algorithm='HS256') # *** Use your SECRET_KEY ***

            # Return the JWT in the response
            return jsonify({
                "message": "Login successful!",
                "token": token # *** Return the generated token ***
            }), 200
        else:
            # Password does not match the hash
            return jsonify({"error": "Invalid username or password."}), 401 # 401 Unauthorized

    except psycopg2.Error as e:
        print(f"Database error during login: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred during login: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_authenticated_user():
    """
    Extracts JWT from Authorization header, verifies it, and returns user payload.
    Returns None if token is missing, invalid, expired, or malformed.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        print("Authentication failed: No Authorization header provided.")
        return None # No Authorization header provided

    parts = auth_header.split()

    # Check if the header starts with "Bearer " and has a token part
    if parts[0].lower() != 'bearer' or len(parts) != 2:
        print("Authentication failed: Invalid Authorization header format.")
        return None # Invalid Authorization header format (e.g., just "Bearer" or something else)

    token = parts[1] # This should be the token string

    # Basic check for empty token string after split (should be caught by len(parts)!=2, but defensive)
    if not token:
         print("Authentication failed: Token part is empty.")
         return None

    try:
        # *** Use your SECRET_KEY for decoding ***
        # Add DecodeError to the exceptions caught to handle malformed tokens gracefully
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

        # Optional: Check if essential keys exist in payload (basic validation)
        if 'user_account_id' not in payload or 'role' not in payload or 'entity_id' not in payload:
             print("JWT payload missing essential keys.")
             return None # Payload missing required keys

        # Return the decoded payload information as a tuple
        return (payload['user_account_id'], payload['role'], payload['entity_id'])

    # *** CORRECTED: Catch specific exception classes directly in a tuple ***
    # Catch InvalidTokenError (signature invalid, audience, issuer etc.),
    # ExpiredSignatureError (token expired), and
    # DecodeError (token format is fundamentally wrong, like "Not enough segments")
    except (InvalidTokenError, ExpiredSignatureError, DecodeError) as e:
        print(f"Authentication failed: JWT validation failed (Invalid/Expired/Malformed) - {e}")
        return None # Authentication failed due to invalid/expired/malformed token
    except Exception as e:
        # Catch any other unexpected errors during decoding process
        print(f"An unexpected error occurred during JWT decoding: {e}")
        return None # Unexpected decoding error

# --- Authentication Decorator ---
def login_required(f):
    """
    Decorator to protect routes, ensuring a user is authenticated.
    Requires get_authenticated_user() to return a user tuple.
    """
    @wraps(f) # Preserves original function metadata
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user() # Check if user is authenticated

        if user is None:
            # If get_authenticated_user returned None, authentication failed
            return jsonify({"error": "Authentication required."}), 401 # 401 Unauthorized

        # Pass the authenticated user tuple to the wrapped function
        # The view function can now access user[0] (user_account_id), user[1] (role), user[2] (entity_id)
        return f(user, *args, **kwargs) # Pass user tuple as the first argument

    return decorated_function

######################################################################################################################################################

# --- Protected Student Profile Route ---
# This route requires a logged-in user (specifically a student)
@app.route('/student/profile', methods=['GET'])
@login_required # Apply the decorator to protect this route
def get_student_profile(user):
    """
    Retrieves the profile and QR data for the logged-in student.
    Requires 'student' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    """
    user_account_id, role, student_id = user # Unpack the user tuple from the decorator

    # --- Role Check: Ensure only students can access this route ---
    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can access this profile."}), 403 # 403 Forbidden


    # --- Fetch Student Profile Data ---
    conn = None
    cur = None
    student_profile = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        # Use RealDictCursor to easily access data by column name
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch student details including the qr_code_data
        # The student_id from the user tuple (entity_id) is the student's primary key
        sql = """
            SELECT
                s.student_id,
                s.first_name,
                s.last_name,
                s.matriculation_number,
                s.level,
                s.intended_program,
                s.email,
                s.contact_number,
                s.date_of_birth,
                s.gender,
                s.admission_date,
                s.qr_code_data, -- Fetch the stored QR data
                d.department_name -- Join to get department name
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            WHERE s.student_id = %s; -- Use the student_id from the authenticated user
        """
        cur.execute(sql, (student_id,)) # Pass the student_id from the user tuple

        student_profile = cur.fetchone()

        if student_profile is None:
            # This should ideally not happen if the student_id in useraccounts is correct
            print(f"Error: Student profile not found for user_account_id {user_account_id} with student_id {student_id}")
            return jsonify({"error": "Student profile not found."}), 404

        return jsonify(student_profile), 200 # Return the student profile data

    except psycopg2.Error as e:
        print(f"Database error fetching student profile: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching student profile: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- Protected Student Dashboard Routes ---
@app.route('/student/schedule', methods=['GET'])
@login_required
def get_student_schedule(user):
    """
    Retrieves the course schedule (sessions) for the logged-in student
    based on their enrollments in studentsenrolledcourses.
    Requires 'student' role.
    """
    user_account_id, role, student_id = user # student_id is the entity_id from useraccounts

    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can view their schedule."}), 403

    conn = None
    cur = None
    schedule_data = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # SQL query updated to use the correct column name: term_name
        sql = """
            SELECT
                c.course_id,
                c.course_code,
                c.course_title,
                c.credits,
                c.level,
                ay.term_name AS academic_year, -- *** Correct column name ***
                s.session_id,
                s.session_datetime,
                s.duration_minutes,
                s.location,
                s.qr_code_expiry_time,
                u.username AS lecturer_username -- Get lecturer username
            FROM studentsenrolledcourses sec
            JOIN courses c ON sec.course_id = c.course_id
            JOIN academicyears ay ON sec.academic_year_id = ay.academic_year_id
            JOIN coursesassignedtolecturers cal ON c.course_id = cal.course_id AND sec.academic_year_id = cal.academic_year_id
            LEFT JOIN attendancesessions s ON cal.assignment_id = s.assignment_id
            LEFT JOIN lecturers l ON cal.lecturer_id = l.lecturer_id
            LEFT JOIN useraccounts u ON l.user_account_id = u.user_account_id
            WHERE sec.student_id = %s -- Filter using student_id (assuming this spelling is correct)
            ORDER BY s.session_datetime NULLS LAST, c.course_code; -- Order by session time, courses without sessions last
        """
        # Use the student_id obtained from the authenticated user's entity_id
        cur.execute(sql, (student_id,))

        schedule_data = cur.fetchall()

        return jsonify(schedule_data), 200

    except psycopg2.Error as e:
        print(f"Database error fetching student schedule: {e}")
        error_message = str(e)
        # Check if the error is specifically about table/column names
        if "relation \"studentsenrolledcourses\" does not exist" in error_message or \
           "relation \"academicyears\" does not exist" in error_message or \
           "relation \"coursesassignedtolecturers\" does not exist" in error_message or \
           "relation \"attendancesessions\" does not exist" in error_message or \
           "relation \"lecturers\" does not exist" in error_message or \
           "relation \"useraccounts\" does not exist" in error_message or \
           "column \"student_id\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message: # Added check for both spellings
             return jsonify({"error": "Configuration error: One or more table/column names are incorrect. Check spelling against your database schema."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching student schedule: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# --- Protected Student Dashboard Routes ---
@app.route('/student/attendance', methods=['GET'])
@login_required
def get_student_attendance(user):
    """
    Retrieves attendance records and summary for the logged-in student
    based on their enrollments in studentsenrolledcourses.
    Requires 'student' role.
    """
    user_account_id, role, student_id = user # student_id is the entity_id from useraccounts

    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can view their attendance."}), 403

    conn = None
    cur = None
    attendance_records = []
    attendance_summary = {}

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Fetch detailed attendance records for this student
        # SQL query updated to use the correct column name: term_name
        sql_records = """
            SELECT
                ar.record_id,
                ar.attendance_time,
                ar.status,
                s.session_id,
                s.session_datetime,
                s.duration_minutes,
                c.course_code,
                c.course_title,
                ay.term_name AS academic_year -- *** Correct column name ***
            FROM attendancerecords ar
            JOIN attendancesessions s ON ar.session_id = s.session_id
            JOIN coursesassignedtolecturers cal ON s.assignment_id = cal.assignment_id
            JOIN courses c ON cal.course_id = c.course_id
            JOIN academicyears ay ON cal.academic_year_id = ay.academic_year_id -- *** Correct table name ***
            JOIN studentsenrolledcourses sec ON ar.student_id = sec.student_id AND c.course_id = sec.course_id AND ay.academic_year_id = sec.academic_year_id
            WHERE ar.student_id = %s
            ORDER BY ar.attendance_time DESC;
        """
        cur.execute(sql_records, (student_id,))
        attendance_records = cur.fetchall()

        # 2. Calculate attendance summary
        # SQL query updated to use the correct column name: term_name
        sql_summary = """
            SELECT
                ar.status,
                COUNT(*) as count
            FROM attendancerecords ar
             JOIN attendancesessions s ON ar.session_id = s.session_id
            JOIN coursesassignedtolecturers cal ON s.assignment_id = cal.assignment_id
            JOIN academicyears ay ON cal.academic_year_id = ay.academic_year_id -- *** Correct table name ***
            JOIN studentsenrolledcourses sec ON ar.student_id = sec.student_id AND cal.course_id = sec.course_id AND ay.academic_year_id = sec.academic_year_id
            WHERE ar.student_id = %s
            GROUP BY ar.status;
        """
        cur.execute(sql_summary, (student_id,))
        summary_rows = cur.fetchall()

        for row in summary_rows:
            attendance_summary[row['status']] = row['count']

        return jsonify({
            "records": attendance_records,
            "summary": attendance_summary
        }), 200

    except psycopg2.Error as e:
        print(f"Database error fetching student attendance: {e}")
        error_message = str(e)
        # Check if the error is specifically about table/column names for common typos
        if "relation \"studentsenrolledcourses\" does not exist" in error_message or \
           "relation \"academicyears\" does not exist" in error_message or \
           "relation \"attendancerecords\" does not exist" in error_message or \
           "relation \"attendancesessions\" does not exist" in error_message or \
           "relation \"coursesassignedtolecturers\" does not exist" in error_message or \
           "relation \"courses\" does not exist" in error_message or \
           "column \"student_id\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message or \
           "column \"ar.status\" does not exist" in error_message: # Added status check
             return jsonify({"error": "Configuration error: One or more table/column names are incorrect. Check spelling against your database schema."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching student attendance: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/student/courses', methods=['GET'])
@login_required # Apply the decorator to protect this route
def get_student_enrolled_courses(user):
    """
    Retrieves the list of courses the logged-in student is enrolled in.
    Requires 'student' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    """
    user_account_id, role, student_id = user # Unpack the user tuple from the decorator
     # Ensure student_id is not None, although login_required should handle this for student role
    if student_id is None:
         return jsonify({"error": "Student entity ID is missing in token."}), 401


    # --- Role Check: Ensure only students can access this route ---
    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can view their enrolled courses."}), 403 # 403 Forbidden


    # --- Fetch Student Enrolled Courses Data ---
    conn = None
    cur = None
    enrolled_courses_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        # Use RealDictCursor to easily access data by column name
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch details of courses the student is enrolled in
        # Join courses and academicyears for details
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                sec.enrollment_id, -- Assuming a unique ID for enrollment
                sec.course_id,
                c.course_code,
                c.course_title,
                c.credits,
                c.level AS course_level,
                sec.academic_year_id,
                ay.term_name AS academic_year_term, -- Academic year term name
                sec.enrollment_date -- Date student enrolled
                -- Include other columns from studentsenrolledcourses if needed
            FROM studentsenrolledcourses sec -- *** Use the correct table name ***
            JOIN courses c ON sec.course_id = c.course_id -- *** Join courses table ***
            JOIN academicyears ay ON sec.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            WHERE sec.student_id = %s -- Filter using the student_id from the authenticated user
            ORDER BY ay.year DESC, ay.term_name, c.course_code; -- Order by year, term, course code
        """
        # Note: Adjust column names (enrollment_id, course_id, academic_year_id, enrollment_date,
        # course_code, course_title, credits, level, term_name) and table names
        # (studentsenrolledcourses, courses, academicyears) if your schema is different.
        # Assumes 'enrollment_id' exists as PK in studentsenrolledcourses.

        # Use the student_id obtained from the authenticated user's entity_id
        cur.execute(sql, (student_id,))

        enrolled_courses_list = cur.fetchall()

        # Optional: Convert dates/timestamps to string format for JSON if needed
        # for course in enrolled_courses_list:
        #      if course.get('enrollment_date'):
        #          course['enrollment_date'] = course['enrollment_date'].isoformat()


        return jsonify(enrolled_courses_list), 200 # Return the list of enrolled courses

    except psycopg2.Error as e:
        print(f"Database error fetching student enrolled courses: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching student enrolled courses: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/student/password', methods=['PUT'])
@login_required # Apply the decorator to protect this route
def change_student_password(user):
    """
    Allows the logged-in student to change their password.
    Requires 'student' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    Requires 'old_password' and 'new_password' in the JSON request body.
    """
    user_account_id, role, student_id = user # Unpack the user tuple from the decorator
    # Ensure user_account_id is not None
    if user_account_id is None:
         # This should be caught by login_required, but added as a safeguard
         return jsonify({"error": "User account ID is missing in token."}), 401


    # --- Role Check: Ensure only students can access this route ---
    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can change their password."}), 403 # 403 Forbidden


    # --- Get Password Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    required_fields = ['old_password', 'new_password']

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    old_password = data.get('old_password')
    new_password = data.get('new_password')

    # Basic validation for new password (e.g., minimum length) - optional but recommended
    if len(new_password) < 6: # Example: minimum 6 characters
        return jsonify({"error": "New password must be at least 6 characters long."}), 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- Verify Old Password ---
        # Fetch the current hashed password for the user account
        # *** VERIFY 'useraccounts' TABLE NAME AND 'user_account_id', 'hashed_password' COLUMNS ***
        cur.execute("SELECT password FROM useraccounts WHERE user_account_id = %s;", (user_account_id,))
        user_account = cur.fetchone()

        if user_account is None:
            # This case should ideally not be reached if token is valid, but good safeguard
            print(f"Error: User account not found for user_account_id {user_account_id} during password change.")
            return jsonify({"error": "User account not found."}), 404 # Or 401/500

        stored_password = user_account[0]

        # Use check_password_hash to compare the provided old password with the stored hash
        if not check_password_hash(stored_password, old_password):
            return jsonify({"error": "Incorrect old password."}), 401 # 401 Unauthorized


        # --- Hash the New Password ---
        hashed_new_password = generate_password_hash(new_password)


        # --- Update the Password in the Database ---
        sql_update_password = """
            UPDATE useraccounts -- *** Use the correct table name ***
            SET password = %s
            WHERE user_account_id = %s; -- Update the logged-in user's password
        """
        cur.execute(sql_update_password, (hashed_new_password, user_account_id))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if user_account was found, but safeguard
             return jsonify({"error": "Password could not be updated."}), 500


        conn.commit()

        return jsonify({"message": "Password updated successfully!"}), 200 # 200 OK

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during password change: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during password change: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/student/profile', methods=['PUT'])
@login_required # Apply the decorator to protect this route
def update_student_profile(user):
    """
    Allows the logged-in student to update specific fields in their profile.
    Requires 'student' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    Accepts update data in the JSON request body.
    Only allows updates to a predefined set of fields.
    """
    user_account_id, role, student_id = user # Unpack the user tuple from the decorator
    # Ensure student_id is not None
    if student_id is None:
         # This should be caught by login_required, but added as a safeguard
         return jsonify({"error": "Student entity ID is missing in token."}), 401


    # --- Role Check: Ensure only students can access this route ---
    if role != 'student':
        return jsonify({"error": "Access forbidden. Only students can update their profile."}), 403 # 403 Forbidden


    # --- Get Update Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Define Allowed Fields for Student Update ---
    # *** CAUTION: Be very selective here! ***
    # Only list fields that a student should be allowed to change themselves.
    # Example: Contact number, maybe personal email (if not used for login), perhaps address fields if they exist.
    # Do NOT include: student_id, first_name, last_name, matriculation_number, level, program,
    # department_id, admission_date, date_of_birth, gender, qr_code_data, etc.
    allowed_updatable_fields = [
        'contact_number'
        # Add other fields students can update, like 'personal_email' (if different from login email)
        # or address fields (e.g., 'street_address', 'city', 'state', 'zip_code') if they exist in your students table
    ]

    update_data = {}
    for field in allowed_updatable_fields:
        # Only include fields present in the request body (allow None or empty strings if nullable in schema)
        if field in data:
            update_data[field] = data[field]


    # If no updatable fields are provided, nothing to do
    if not update_data:
        # Decide if you want 200 with message or 400 error
        return jsonify({"message": "No valid updatable fields provided in the request body."}), 200


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions

        # --- Optional Validation for Specific Fields ---
        # If you allow updating email, you might need format validation or verification workflow
        # If you allow updating contact_number, you might add format validation here
        # Example: Basic contact_number format check (simple)
        # if 'contact_number' in update_data and update_data['contact_number']:
        #      if not re.fullmatch(r'^\d{3}-\d{3}-\d{4}$', update_data['contact_number']): # Example format XXX-XXX-XXXX
        #           return jsonify({"error": "Invalid contact number format. Use XXX-XXX-XXXX."}), 400
        # Ensure 'import re' at the top if using regex validation


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No fields to update."}), 200 # Should be caught above


        sql_update = f"""
            UPDATE students -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE student_id = %s; -- Update the logged-in student's record
        """
        # Pass values from update_data followed by the student_id for the WHERE clause
        execute_values = list(update_data.values()) + [student_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             # This might happen if student_id from token doesn't match a record (shouldn't with safeguards)
             # or if the update data is exactly the same as current data.
             return jsonify({"message": "Student profile found, but no changes were applied (data might be the same or no updatable fields provided)."}), 200


        conn.commit()

        # Optional: Re-fetch and return the updated profile details
        # You could call get_student_profile(user) here or copy its fetch logic
        # For simplicity, just return a success message
        return jsonify({"message": "Student profile updated successfully!"}), 200 # 200 OK

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during student profile update: {e}")
        # Might happen if a unique constraint is violated (e.g., updating email if it's unique)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during student profile update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during student profile update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/student/notifications', methods=['GET'])
@login_required # Protect this route
def list_relevant_notifications_for_student(user):
    """
    Retrieves a list of notifications relevant to the logged-in student.
    Requires 'student' role.
    """
    user_account_id_student, role_student, student_id = user # Unpack the student user tuple

    # --- Role Check: Ensure only students can access this route ---
    if role_student != 'student':
        return jsonify({"error": "Access forbidden. Only students can view their relevant notifications."}), 403

    conn = None
    cur = None
    notifications_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # --- Get Context for Filtering (Student's Department and Enrolled Courses) ---
        # Fetch the student's department ID
        cur.execute("SELECT department_id FROM students WHERE student_id = %s;", (student_id,))
        student_dept_row = cur.fetchone()

        # --- DEBUG PRINT ---
        print(f"DEBUG: student_id: {student_id}")
        print(f"DEBUG: student_dept_row: {student_dept_row} (Type: {type(student_dept_row)})")
        # --- END DEBUG PRINT ---

        if student_dept_row is None:
             print(f"Error: Student department not found for student_id {student_id} during notification fetch.")
             return jsonify({"error": "Student department not found."}), 404 # Changed to 404 Not Found

        # Access department_id from the fetched row (should be a dictionary)
        student_department_id = student_dept_row['department_id']


        # Fetch the list of course IDs the student is enrolled in (in any academic year)
        sql_get_student_courses = """
            SELECT DISTINCT course_id
            FROM studentsenrolledcourses -- Correct table name
            WHERE student_id = %s; -- Filter by logged-in student ID
        """
        cur.execute(sql_get_student_courses, (student_id,))
        fetched_courses = cur.fetchall() # Fetch all results first

        # --- DEBUG PRINT ---
        print(f"DEBUG: fetched_courses from sql_get_student_courses: {fetched_courses} (Type: {type(fetched_courses)})")
        # --- END DEBUG PRINT ---

        # Process the fetched list into just a list of course IDs
        student_enrolled_course_ids = [row['course_id'] for row in fetched_courses]

        # --- DEBUG PRINT ---
        print(f"DEBUG: student_department_id: {student_department_id} (Type: {type(student_department_id)})") # Print again after getting value
        print(f"DEBUG: student_enrolled_course_ids: {student_enrolled_course_ids} (Type: {type(student_enrolled_course_ids)})")
        # --- END DEBUG PRINT ---


        # --- Fetch Relevant Notifications Data ---
        sql = """
            SELECT
                n.notification_id,
                n.title,
                n.message,
                n.created_at,
                n.created_by_user_account_id,
                ua.username AS creator_username,
                ua.role AS creator_role,
                n.target_role,
                n.target_department_id,
                d.department_name AS target_department_name,
                n.target_course_id,
                c.course_code AS target_course_code,
                c.course_title AS target_course_title
            FROM notifications n
            JOIN useraccounts ua ON n.created_by_user_account_id = ua.user_account_id
            LEFT JOIN departments d ON n.target_department_id = d.department_id
            LEFT JOIN courses c ON n.target_course_id = c.course_id
            WHERE
                n.target_role = 'All'
                OR n.target_role = 'Student'
                OR (n.target_role = 'Department' AND n.target_department_id = %s)
                OR (n.target_role = 'Course' AND n.target_course_id = ANY(%s::VARCHAR[]))
            ORDER BY n.created_at DESC;
        """
        # Pass parameters: student_department_id, student_enrolled_course_ids (as a list/array)
        cur.execute(sql, (student_department_id, student_enrolled_course_ids)) # Execute the main query

        notifications_list = cur.fetchall() # Fetch the results

        # Optional: Convert timestamps to string format for JSON if needed


        return jsonify(notifications_list), 200

    except psycopg2.Error as e:
        # ... (database error handling) ...
        print(f"Database error fetching student notifications: {e}")
        error_message = str(e)
        # Add checks for specific table/column names if needed
        # The "tuple index out of range" is likely happening before here, but keep this general catch
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
            return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        # ... (general error handling) ...
        print(f"An unexpected error occurred fetching student notifications: {e}")
        # The "tuple index out of range" error will likely be printed here
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

######################################################################################################################################################

# --- Protected Lecturer Dashboard Routes (Attendance Management) ---

@app.route('/lecturer/profile', methods=['GET'])
@login_required # Apply the decorator to protect this route
def get_lecturer_profile(user):
    """
    Retrieves the profile for the logged-in lecturer.
    Requires 'lecturer' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id for lecturers

    # --- Role Check: Ensure only lecturers can access this route ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can access this profile."}), 403 # 403 Forbidden


    # --- Fetch Lecturer Profile Data ---
    conn = None
    cur = None
    lecturer_profile = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        # Use RealDictCursor to easily access data by column name
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch lecturer details
        # Assuming 'lecturers' table has columns like employee_id, first_name, last_name, email, contact_number, department_id
        # Join with 'departments' to get the department name
        sql = """
            SELECT
                l.lecturer_id, -- Or employee_id if that's the PK you use here
                l.first_name,
                l.last_name,
                l.employee_id, -- If employee_id is separate from lecturer_id PK
                l.email,
                l.contact_number,
                l.date_of_employment,
                d.department_name, -- Department name from departments table
                ua.username AS user_account_username -- Get username from useraccounts
            FROM lecturers l
            JOIN departments d ON l.department_id = d.department_id
            JOIN useraccounts ua ON l.user_account_id = ua.user_account_id -- Join to get username
            WHERE l.lecturer_id = %s; -- *** Filter by the lecturer_id from the authenticated user's entity_id ***
        """
        # Use the lecturer_id obtained from the authenticated user's entity_id
        cur.execute(sql, (lecturer_id,)) # Pass the lecturer_id from the user tuple

        lecturer_profile = cur.fetchone()

        if lecturer_profile is None:
            # This should ideally not happen if the entity_id in useraccounts is correct
            print(f"Error: Lecturer profile not found for user_account_id {user_account_id} with lecturer_id {lecturer_id}")
            return jsonify({"error": "Lecturer profile not found."}), 404

        return jsonify(lecturer_profile), 200 # Return the lecturer profile data

    except psycopg2.Error as e:
        print(f"Database error fetching lecturer profile: {e}")
        # Add checks for specific table/column names if needed, like we did for student routes
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching lecturer profile: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/courses', methods=['GET'])
@login_required # Protect this route
def get_lecturer_assigned_courses(user):
    """
    Retrieves the list of courses assigned to the logged-in lecturer.
    Requires 'lecturer' role.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view their assigned courses."}), 403


    # --- Fetch Assigned Courses Data ---
    conn = None
    cur = None
    assigned_courses = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select courses assigned to this lecturer
        # Join coursesassignedtolecturers with courses and academicyears for details
        sql = """
            SELECT
                cal.assignment_id, -- The assignment identifier
                c.course_id,
                c.course_code,
                c.course_title,
                c.credits,
                c.level,
                ay.academic_year_id,
                ay.term_name AS academic_year -- Get academic year name (check column name - could be term_name)
            FROM coursesassignedtolecturers cal -- *** Correct table name ***
            JOIN courses c ON cal.course_id = c.course_id -- Correct table name
            JOIN academicyears ay ON cal.academic_year_id = ay.academic_year_id -- *** Correct table name ***
            WHERE cal.lecturer_id = %s -- *** Filter by the lecturer_id from the authenticated user's entity_id ***
            ORDER BY ay.term_name DESC, c.course_code; -- Order by academic year and course code (check column name for year name)
        """
        # Use the lecturer_id obtained from the authenticated user's entity_id
        cur.execute(sql, (lecturer_id,)) # Pass the lecturer_id from the user tuple

        assigned_courses = cur.fetchall()

        return jsonify(assigned_courses), 200

    except psycopg2.Error as e:
        print(f"Database error fetching lecturer assigned courses: {e}")
        # Add checks for specific table/column names if needed
        error_message = str(e)
        if "relation \"coursesassignedtolecturers\" does not exist" in error_message or \
           "relation \"courses\" does not exist" in error_message or \
           "relation \"academicyears\" does not exist" in error_message or \
           "relation \"lecturers\" does not exist" in error_message or \
           "column \"cal.lecturer_id\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message or \
           "column \"ay.term_name\" does not exist" in error_message: # Added check for term_name/term_name
             return jsonify({"error": "Configuration error: One or more table/column names are incorrect. Check spelling against your database schema."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching lecturer assigned courses: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/assignments/<assignment_id>/sessions', methods=['GET'])
@login_required # Protect this route
def get_lecturer_assignment_sessions(user, assignment_id):
    """
    Retrieves the list of sessions for a specific course assignment.
    Requires 'lecturer' role.
    Requires the assignment to be assigned to the logged-in lecturer.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view sessions for assignments."}), 403

    conn = None
    cur = None
    sessions_data = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # --- Security Check: Verify the assignment belongs to the logged-in lecturer ---
        # Prevent lecturers from viewing sessions for assignments they don't own
        sql_verify_assignment = """
            SELECT assignment_id
            FROM coursesassignedtolecturers -- *** Correct table name ***
            WHERE assignment_id = %s AND lecturer_id = %s; -- *** Check both assignment ID and logged-in lecturer ID ***
        """
        cur.execute(sql_verify_assignment, (assignment_id, lecturer_id))
        assignment_owner = cur.fetchone()

        if assignment_owner is None:
            # Assignment not found OR it doesn't belong to this lecturer
            return jsonify({"error": "Assignment not found or you do not have permission to view its sessions."}), 404 # Or 403 if you prefer to distinguish


        # --- Fetch Sessions for the Assignment ---
        sql_sessions = """
            SELECT
                s.session_id,
                s.session_datetime,
                s.duration_minutes,
                s.location,
                s.qr_code_expiry_time,
                s.assignment_id -- Include assignment_id for context
            FROM attendancesessions s -- *** Correct table name ***
            WHERE s.assignment_id = %s -- Filter by the assignment ID from the URL
            ORDER BY s.session_datetime; -- Order sessions chronologically
        """
        # Use the assignment_id from the URL path parameter
        cur.execute(sql_sessions, (assignment_id,))

        sessions_data = cur.fetchall()

        return jsonify(sessions_data), 200

    except psycopg2.Error as e:
        print(f"Database error fetching assignment sessions: {e}")
        # Add checks for specific table/column names if needed
        error_message = str(e)
        if "relation \"coursesassignedtolecturers\" does not exist" in error_message or \
           "relation \"attendancesessions\" does not exist" in error_message or \
           "column \"lecturer_id\" does not exist" in error_message: # Check for lecturer_id in assignments table typo
             return jsonify({"error": "Configuration error: One or more table/column names are incorrect. Check spelling against your database schema."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching assignment sessions: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/assignments/<assignment_id>/students', methods=['GET'])
@login_required # Apply the decorator to protect this route
def get_students_for_lecturer_assignment(user, assignment_id):
    """
    Retrieves the list of students enrolled in the course and academic year
    of a specific course assignment.
    Requires 'lecturer' role.
    Requires the assignment to be assigned to the logged-in lecturer.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view student lists for assignments."}), 403

    conn = None
    cur = None
    students_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # --- Security Check: Verify the assignment belongs to the logged-in lecturer and get course/year IDs ---
        # This query checks ownership and gets the necessary course_id and academic_year_id for filtering studentsenrolledcourses
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND COLUMNS ***
        sql_verify_assignment_owner = """
            SELECT cal.course_id, cal.academic_year_id
            FROM coursesassignedtolecturers cal -- Correct table name
            WHERE cal.assignment_id = %s AND cal.lecturer_id = %s; -- Check both assignment ID and logged-in lecturer ID
        """
        cur.execute(sql_verify_assignment_owner, (assignment_id, lecturer_id))
        assignment_info = cur.fetchone()

        if assignment_info is None:
            # Assignment not found OR it doesn't belong to this lecturer
            return jsonify({"error": "Assignment not found or you do not have permission to view its student list."}), 404 # Or 403 if you prefer to distinguish

        # Extract the course_id and academic_year_id from the assignment
        course_id = assignment_info['course_id']
        academic_year_id = assignment_info['academic_year_id']

        # --- Fetch Students Enrolled in this Course and Academic Year ---
        # Query studentsenrolledcourses, filtering by the course_id and academic_year_id from the assignment
        # Join students table for student details
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql_students = """
            SELECT
                sec.enrollment_id, -- Optional, but good to include enrollment context
                sec.student_id,    -- FK to students
                s.first_name,      -- From joined students
                s.last_name,       -- From joined students
                s.matriculation_number -- From joined students
                -- Include other student profile columns relevant for a class list if needed
            FROM studentsenrolledcourses sec -- *** Use the correct table name ***
            JOIN students s ON sec.student_id = s.student_id -- *** Join students table ***
            WHERE sec.course_id = %s AND sec.academic_year_id = %s -- *** Filter by the course and year of the assignment ***
            ORDER BY s.last_name, s.first_name; -- Order by student name
        """
        # Use the course_id and academic_year_id obtained from the assignment
        cur.execute(sql_students, (course_id, academic_year_id))

        students_list = cur.fetchall()

        return jsonify(students_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching students for assignment {assignment_id}: {e}")
        # Add checks for specific table/column names if needed
        error_message = str(e)
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
            return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching students for assignment {assignment_id}: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/sessions', methods=['GET'])
@login_required # Apply the decorator to protect this route
def get_all_lecturer_sessions(user):
    """
    Retrieves a list of all attendance sessions for all assignments
    assigned to the logged-in lecturer.
    Requires 'lecturer' role.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view their sessions list."}), 403

    conn = None
    cur = None
    sessions_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all sessions linked to assignments assigned to this lecturer
        # Join through coursesassignedtolecturers to filter by lecturer_id
        # Join other tables for context (Course, Year)
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                ats.session_id,      -- Primary key
                ats.assignment_id,   -- FK to coursesassignedtolecturers
                ca.semester,         -- From joined coursesassignedtolecturers
                ca.course_id,        -- FK to courses (via ca)
                c.course_code,       -- From joined courses
                c.course_title,      -- From joined courses
                ca.academic_year_id, -- FK to academicyears (via ca)
                ay.term_name AS academic_year_term, -- From joined academicyears
                ats.session_datetime, -- Timestamp column
                ats.duration_minutes, -- Duration
                ats.location          -- Location
                -- Include other columns from attendancesessions if needed (qr_code_expiry_time, created_at)
            FROM attendancesessions ats -- *** Use the correct table name ***
            JOIN coursesassignedtolecturers ca ON ats.assignment_id = ca.assignment_id -- *** Join coursesassignedtolecturers ***
            JOIN courses c ON ca.course_id = c.course_id -- *** Join courses table ***
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            WHERE ca.lecturer_id = %s -- *** Filter by the logged-in lecturer's ID from the assignment table ***
            ORDER BY ats.session_datetime DESC; -- Order sessions chronologically
        """
        # Note: Adjust column names and table names if your schema is different.
        # Make sure you use the correct column name for academic year term name.
        # Make sure session_datetime, duration_minutes, location exist and are correct.


        # Use the lecturer_id obtained from the authenticated user's entity_id
        cur.execute(sql, (lecturer_id,)) # Pass the lecturer_id from the user tuple

        sessions_list = cur.fetchall()

        # Optional: Convert timestamps to string format for JSON if needed
        # for session in sessions_list:
        #     if session.get('session_datetime'):
        #         session['session_datetime'] = session['session_datetime'].isoformat()


        return jsonify(sessions_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching all lecturer sessions: {e}")
        # Add checks for specific table/column names if needed
        error_message = str(e)
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
            return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching all lecturer sessions: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/sessions/<session_id>/attendance', methods=['GET'])
@login_required # Protect this route
def get_lecturer_session_attendance(user, session_id):
    """
    Retrieves attendance records for a specific session.
    Requires 'lecturer' role.
    Requires the session's assignment to be assigned to the logged-in lecturer.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view attendance records."}), 403

    conn = None
    cur = None
    attendance_records = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # --- Security Check: Verify the session belongs to an assignment owned by the logged-in lecturer ---
        # Join sessions to assignments and check if the assignment belongs to this lecturer
        sql_verify_session_ownership = """
            SELECT s.session_id
            FROM attendancesessions s -- Correct table name
            JOIN coursesassignedtolecturers cal ON s.assignment_id = cal.assignment_id -- Correct table name
            WHERE s.session_id = %s AND cal.lecturer_id = %s; -- Check both session ID and logged-in lecturer ID
        """
        cur.execute(sql_verify_session_ownership, (session_id, lecturer_id))
        session_owner = cur.fetchone()

        if session_owner is None:
            # Session not found OR its assignment doesn't belong to this lecturer
            return jsonify({"error": "Session not found or you do not have permission to view its attendance."}), 404


        # --- Fetch Attendance Records for the Session ---
        # Join attendancerecords with students to get student names
        # *** MODIFIED: Corrected s.student_id to ar.student_id ***
        sql_records = """
            SELECT
                ar.record_id,
                ar.attendance_time,
                ar.status, -- e.g., 'Present', 'Absent', 'Late'
                ar.student_id, -- *** CORRECTED: Use 'ar' alias for student_id ***
                st.first_name,
                st.last_name,
                st.matriculation_number
            FROM attendancerecords ar -- Use 'ar' alias
            JOIN students st ON ar.student_id = st.student_id -- Use 'st' alias
            WHERE ar.session_id = %s -- Filter by the session ID from the URL
            ORDER BY st.matriculation_number; -- Order by student matric number
        """
        # Use the session_id from the URL path parameter
        cur.execute(sql_records, (session_id,))

        attendance_records = cur.fetchall()

        return jsonify(attendance_records), 200

    except psycopg2.Error as e:
        print(f"Database error fetching session attendance records: {e}")
        error_message = str(e)
        # Add checks for specific table/column names if needed
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
             return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching session attendance records: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/sessions/<session_id>/records', methods=['POST'])
@login_required # Apply the decorator to protect this route
def submit_attendance_records_for_session(user, session_id):
    """
    Submits attendance records for a specific session.
    Accepts a list of attendance records in the JSON request body.
    Requires 'lecturer' role.
    Requires the session's assignment to be assigned to the logged-in lecturer.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can submit attendance records."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    records_data_list = request.get_json()

    # Ensure the request body is a list
    if not isinstance(records_data_list, list):
        return jsonify({"error": "Request body must be a JSON list of attendance records."}), 400

    if not records_data_list:
         return jsonify({"message": "No attendance records provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    successful_creations = []
    failed_creations = []
    records_to_insert = [] # List of tuples for batch insert


    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # --- Security Check: Verify the session belongs to an assignment owned by the logged-in lecturer ---
        # Join sessions to assignments and check if the assignment belongs to this lecturer
        sql_verify_session_ownership = """
            SELECT s.session_id
            FROM attendancesessions s -- Correct table name
            JOIN coursesassignedtolecturers cal ON s.assignment_id = cal.assignment_id -- Correct table name
            WHERE s.session_id = %s AND cal.lecturer_id = %s; -- Check both session ID and logged-in lecturer ID
        """
        cur.execute(sql_verify_session_ownership, (session_id, lecturer_id))
        session_owner = cur.fetchone()

        if session_owner is None:
            # Session not found OR its assignment doesn't belong to this lecturer
            return jsonify({"error": "Session not found or you do not have permission to submit attendance for it."}), 404 # Or 403


        # --- Validate and Prepare Records for Insertion ---
        # Fetch existing records for this session to quickly check for duplicates
        # This is more efficient than individual checks in the loop if there are many records
        # *** VERIFY 'attendancerecords' TABLE NAME AND 'session_id', 'student_id' COLUMNS ***
        cur.execute("SELECT session_id, student_id FROM attendancerecords WHERE session_id = %s;", (session_id,))
        existing_records = {(row[0], row[1]) for row in cur.fetchall()} # Store as a set of (session_id, student_id) tuples

        # Fetch valid student IDs to validate incoming student_ids
        # *** VERIFY 'students' TABLE NAME AND 'student_id' COLUMN ***
        cur.execute("SELECT student_id FROM students;") # Fetch all student IDs
        valid_student_ids = {row[0] for row in cur.fetchall()} # Store as a set

        # Define allowed attendance statuses (adjust if needed)
        allowed_statuses = ['Present', 'Absent', 'Late', 'Excused']


        for index, record_data in enumerate(records_data_list):
            # Validate each item in the list is a dictionary
            if not isinstance(record_data, dict):
                failed_creations.append({"index": index, "error": "Record must be a JSON object."})
                continue

            # Validate required fields within the record
            required_record_fields = ['student_id', 'status'] # attendance_time can be defaulted
            missing_fields = [field for field in required_record_fields if field not in record_data or record_data.get(field) is None]
            if missing_fields:
                failed_creations.append({"index": index, "student_id": record_data.get('student_id', 'N/A'), "error": f"Missing required fields: {', '.join(missing_fields)}"})
                continue

            student_id = record_data.get('student_id')
            status = record_data.get('status')
            attendance_time_str = record_data.get('attendance_time') # Optional

            # More detailed validation for fields
            if not isinstance(student_id, str) or not student_id.strip():
                 failed_creations.append({"index": index, "student_id": student_id, "error": "Invalid or empty student_id."})
                 continue
            if not isinstance(status, str) or status not in allowed_statuses:
                 failed_creations.append({"index": index, "student_id": student_id, "error": f"Invalid or unsupported status: '{status}'. Allowed: {', '.join(allowed_statuses)}."})
                 continue

            # Check if student_id is a valid existing student
            if student_id not in valid_student_ids:
                 failed_creations.append({"index": index, "student_id": student_id, "error": f"Student ID '{student_id}' does not exist."})
                 continue


            # Check for duplicate record for this session and student
            if (session_id, student_id) in existing_records:
                failed_creations.append({"index": index, "student_id": student_id, "error": "Attendance record for this student in this session already exists. Use PUT to update."})
                continue

            # Validate and parse optional attendance_time if provided
            attendance_time_obj = None
            if attendance_time_str:
                 try:
                      # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
                      attendance_time_obj = datetime.fromisoformat(attendance_time_str)
                      # Handle potential timezone information if necessary
                 except (ValueError, TypeError):
                      failed_creations.append({"index": index, "student_id": student_id, "error": "Invalid attendance_time format. Use YYYY-MM-DD HH:MM:SS or ISO 8601."})
                      continue

            # Prepare data tuple for insertion (record_id and created_at are generated by DB)
            records_to_insert.append((
                 session_id,
                 student_id,
                 attendance_time_obj, # Pass datetime object or None
                 status,
                 # Add other columns here if needed
            ))
            # Add successful creation to a temporary list for response
            successful_creations.append({"index": index, "student_id": student_id, "status": status})


        # --- Batch Insert Valid Records ---
        if records_to_insert:
             # Define the INSERT statement structure
             # Exclude record_id (generated), created_at (default)
             # *** VERIFY column names match your schema ***
             sql_insert_batch = """
                 INSERT INTO attendancerecords (session_id, student_id, attendance_time, status) -- *** Adjust column names ***
                 VALUES %s
                 ON CONFLICT (session_id, student_id) DO NOTHING; -- Safety net for true race conditions, though manual check is primary
             """
             # Use execute_values for batch insertion
             # It automatically handles formatting the list of tuples for the VALUES clause
             psycopg2.extras.execute_values(cur, sql_insert_batch, records_to_insert)

             # Note: execute_values does NOT return the IDs of the inserted rows easily.
             # If you need the generated record_ids for the response, you might need a different approach,
             # like individual inserts with RETURNING record_id, or querying after the batch insert.
             # For simplicity here, we return the student_id/status of successfully *attempted* inserts.

        conn.commit()

        # --- Prepare Final Response ---
        response_message = f"Attempted to create {len(records_data_list)} attendance records for session {session_id}. "
        response_message += f"Successfully processed {len(records_to_insert)} for insertion. "
        response_message += f"Failed for {len(failed_creations)} records due to validation/duplicates."

        return jsonify({
            "message": response_message,
            "successfully_processed": successful_creations, # Records that passed initial validation and were attempted inserted
            "failed_records": failed_creations # Records that failed validation or were identified as duplicates
            # Note: Does not confirm DB insert success for each batch item, just that they were sent.
            # For more precise confirmation, individual inserts or a follow-up query is needed.
        }), 200 # 200 OK

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during batch attendance record submission for session {session_id}: {e}")
        # This could happen if FK constraints fail despite manual check (very rare),
        # or other DB issues during batch insert.
        return jsonify({"error": f"Database error during submission: {e}"}), 500

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during batch attendance record submission for session {session_id}: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/sessions', methods=['POST'])
@login_required # Protect this route
def create_attendance_session(user):
    """
    Allows a lecturer to create a new attendance session for a course assignment.
    Requires 'lecturer' role.
    Accepts JSON body with 'assignment_id' and 'duration_minutes'.
    """
    user_account_id_lecturer, role_lecturer, entity_id_lecturer = user # Unpack the lecturer user tuple

    # --- Role Check: Ensure only lecturers can access this route ---
    if role_lecturer != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can create attendance sessions."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    assignment_id = data.get('assignment_id')
    duration_minutes = data.get('duration_minutes') # Get duration from request body
    # Optional: Get location from request body if you want to set it
    # location = data.get('location')

    # --- Basic Input Validation ---
    if not assignment_id:
        return jsonify({"error": "Assignment ID is required."}), 400
    if not isinstance(duration_minutes, (int, float)) or duration_minutes <= 0:
        return jsonify({"error": "Valid positive duration (in minutes) is required."}), 400

    conn = None
    cur = None
    cur_dict = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Use standard cursor for simple fetches by index
        cur_dict = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use dict cursor for SELECTs and returning dict

        # --- Step 1: Verify the course assignment exists and is assigned to this lecturer ---
        # Use standard cursor for simple fetch by index
        cur.execute("""
            SELECT assignment_id
            FROM coursesassignedtolecturers -- Use the correct table name
            WHERE assignment_id = %s AND lecturer_id = %s; -- Use the correct column name and lecturer_id
        """, (assignment_id, entity_id_lecturer)) # entity_id_lecturer is the lecturer_id
        assignment_exists = cur.fetchone()

        if assignment_exists is None:
            return jsonify({"error": "Course assignment not found or not assigned to this lecturer."}), 404

        # --- Step 2: Create the Attendance Session ---
        # Use the column name from your schema: session_datetime
        session_datetime = datetime.now(timezone.utc)

        # We don't insert end_time into your schema, we insert duration_minutes
        # You could calculate end_time here if you needed it for other logic
        # end_time = session_datetime + timedelta(minutes=duration_minutes)

        # Calculate QR code expiry time (e.g., session_datetime + duration_minutes)
        qr_code_expiry_time = session_datetime + timedelta(minutes=duration_minutes)


        # *** CORRECTED: Use the correct column names from your schema in the INSERT query ***
        # *** VERIFIED: attendancesessions has assignment_id, session_datetime, duration_minutes, location, qr_code_expiry_time ***
        sql_insert_session = """
            INSERT INTO attendancesessions (assignment_id, session_datetime, duration_minutes, qr_code_expiry_time, location) -- Use your schema's column names
            VALUES (%s, %s, %s, %s, %s)
            RETURNING session_id, assignment_id, session_datetime, duration_minutes, location, qr_code_expiry_time, created_at; -- Return all columns based on your schema
        """
        # Pass the correct values matching the column order in the INSERT statement
        # Pass location (can be None if not in request), and calculated qr_code_expiry_time
        cur_dict.execute(sql_insert_session, (assignment_id, session_datetime, duration_minutes, qr_code_expiry_time, None)) # Assuming location can be null, pass None for now

        new_session_details = cur_dict.fetchone() # Fetch the returned details as a dictionary

        # *** Verify the RETURNING clause matches your attendancesessions table structure ***


        conn.commit()

        # Format timestamps (like session_datetime, qr_code_expiry_time, and created_at if you return it) to ISO 8601 string for JSON response
        if new_session_details:
            if 'session_datetime' in new_session_details and new_session_details['session_datetime']:
                 new_session_details['session_datetime'] = new_session_details['session_datetime'].isoformat()
            if 'qr_code_expiry_time' in new_session_details and new_session_details['qr_code_expiry_time']:
                 new_session_details['qr_code_expiry_time'] = new_session_details['qr_code_expiry_time'].isoformat()
            if 'created_at' in new_session_details and new_session_details['created_at']:
                 new_session_details['created_at'] = new_session_details['created_at'].isoformat()
            # duration_minutes is already a number, location is already a string (or None)


        return jsonify({
            "message": "Attendance session created successfully.",
            "session": new_session_details # Return the details of the new session
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
         if conn: conn.rollback()
         print(f"Integrity error creating attendance session: {e}")
         # Handle potential foreign key violation if assignment ID is invalid in attendancesessions
         # or other integrity errors
         error_message = str(e)
         if 'violates foreign key constraint' in error_message and '"attendancesessions_assignment_id_fkey"' in error_message: # Adjust constraint name if different
              return jsonify({"error": f"Database error: Invalid assignment ID '{assignment_id}'."}), 409
         return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict


    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Database error creating attendance session: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"An unexpected error occurred creating attendance session: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if cur_dict: # Close the dict cursor if it was opened
             cur_dict.close()
        if conn:
            conn.close()

@app.route('/lecturer/records/<record_id>', methods=['PUT'])
@login_required # Apply the decorator to protect this route
def update_lecturer_attendance_record(user, record_id):
    """
    Updates details of a specific attendance record by record_id.
    Requires 'lecturer' role.
    Requires the record to belong to a session assigned to the logged-in lecturer.
    Accepts update data (e.g., status, attendance_time) in the JSON request body.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can update attendance records."}), 403

    # --- Get Update Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Define Allowed Fields for Lecturer Update ---
    # Lecturer should typically only update status and maybe correct the attendance_time
    # Do NOT allow changing record_id, session_id, student_id, created_at
    allowed_updatable_fields = [
        'status',            # e.g., 'Present', 'Absent', 'Late', 'Excused'
        'attendance_time'    # Timestamp when attendance was recorded (optional)
        # Add other specific columns if lecturers can update them
    ]

    update_data = {}
    validated_data = {} # Use a separate dict for fields after validation/parsing

    conn = None
    cur = None
    cur_fetch = None # Cursor for fetching updated details

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions

        # --- Security Check: Verify the record exists and belongs to a session owned by the logged-in lecturer ---
        # Join attendancerecords to sessions and assignments to check ownership
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql_verify_record_ownership = """
            SELECT atr.record_id
            FROM attendancerecords atr -- Correct alias
            JOIN attendancesessions ats ON atr.session_id = ats.session_id -- Correct table names
            JOIN coursesassignedtolecturers cal ON ats.assignment_id = cal.assignment_id -- Correct table names
            WHERE atr.record_id = %s AND cal.lecturer_id = %s; -- Check record ID and logged-in lecturer ID
        """
        cur.execute(sql_verify_record_ownership, (record_id, lecturer_id))
        record_owner = cur.fetchone()

        if record_owner is None:
            # Record not found OR it does not belong to a session taught by this lecturer
            return jsonify({"error": "Attendance record not found or you do not have permission to update it."}), 404 # Or 403


        # --- Validate and Prepare Updatable Fields ---
        # Define allowed attendance statuses (adjust if needed)
        allowed_statuses = ['Present', 'Absent', 'Late', 'Excused']

        for field in allowed_updatable_fields:
             if field in data: # Only process if the field is in the request body
                 value = data[field]

                 # Perform specific validation based on field
                 if field == 'status':
                     # Validate status value
                     if not isinstance(value, str) or value not in allowed_statuses:
                          return jsonify({"error": f"Invalid or unsupported status: '{value}'. Allowed: {', '.join(allowed_statuses)}."}), 400
                     validated_data[field] = value # Use the validated value

                 elif field == 'attendance_time':
                     # Validate and parse timestamp field (allow null if schema allows)
                     if value is None: # Allow setting to null if schema allows
                          validated_data[field] = None
                     elif isinstance(value, str):
                          try:
                               # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
                               timestamp_obj = datetime.fromisoformat(value)
                               validated_data[field] = timestamp_obj # Use the parsed datetime object
                          except (ValueError, TypeError): # Catch TypeError if value is not a string
                               return jsonify({"error": f"Invalid timestamp format for '{field}'. Use-MM-DD HH:MM:SS or ISO 8601."}), 400
                     else: # Value is not None or string
                          return jsonify({"error": f"Invalid data type for '{field}'. Must be string or null."}), 400


                 else:
                     # For other allowed updatable fields, just add the value directly
                     validated_data[field] = value


        # Use the validated_data for the update
        update_data = validated_data

        # If no updatable fields were successfully validated/processed, nothing to do
        if not update_data:
             return jsonify({"message": "No valid updatable fields provided in the request body."}), 200


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No fields to set."}), 200 # Should be caught above


        sql_update = f"""
            UPDATE attendancerecords -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE record_id = %s; -- Filter by the record_id from the URL path
        """
        execute_values = list(update_data.values()) + [record_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             # This might happen if record_id from check didn't translate to update
             return jsonify({"message": "Attendance record found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()

        # Fetch and return the updated record details including joined data
        # Re-use the fetch logic from GET /admin/attendance-records/<record_id>
        cur_fetch = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor
        sql_fetch = """
            SELECT
                atr.record_id, atr.session_id, ats.session_datetime, ats.duration_minutes, ats.location AS session_location,
                atr.student_id, s.first_name AS student_first_name, s.last_name AS student_last_name,
                atr.attendance_time, atr.status, atr.created_at
                -- Include other columns if they exist
            FROM attendancerecords atr
            JOIN attendancesessions ats ON atr.session_id = ats.session_id
            JOIN students s ON atr.student_id = s.student_id
            WHERE atr.record_id = %s;
        """
        cur_fetch.execute(sql_fetch, (record_id,))
        updated_record_details = cur_fetch.fetchone()
        # cur_fetch.close() # Handled in finally


        # Optional: Convert timestamps to string format for JSON if needed in response
        # if updated_record_details:
        #      if updated_record_details.get('session_datetime'):
        #          updated_record_details['session_datetime'] = updated_record_details['session_datetime'].isoformat()
        #      if updated_record_details.get('attendance_time'):
        #          updated_record_details['attendance_time'] = updated_record_details['attendance_time'].isoformat()
        #      if updated_record_details.get('created_at'):
        #          updated_record_details['created_at'] = updated_record_details['created_at'].isoformat()


        return jsonify(updated_record_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance record update: {e}")
        # This shouldn't happen if allowed_updatable_fields prevents FK/unique constraint columns,
        # but included for safety.
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except (psycopg2.Error, ValueError, TypeError) as e: # Catch DB errors and parsing errors
        if conn:
            conn.rollback()
        print(f"Database or data processing error during attendance record update: {e}")
        # Specific checks for e type might be needed for more granular error responses
        return jsonify({"error": f"Database or data processing error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance record update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if cur_fetch: # Close the fetch cursor if it was opened
             cur_fetch.close()
        if conn:
            conn.close()

@app.route('/lecturer/password', methods=['PUT'])
@login_required # Apply the decorator to protect this route
def change_lecturer_password(user):
    """
    Allows the logged-in lecturer to change their password.
    Requires 'lecturer' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    Requires 'old_password' and 'new_password' in the JSON request body.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple from the decorator
    # Ensure user_account_id is not None
    if user_account_id is None:
         # This should be caught by login_required, but added as a safeguard
         return jsonify({"error": "User account ID is missing in token."}), 401


    # --- Role Check: Ensure only lecturers can access this route ---
    if role != 'lecturer': # *** Role check for 'lecturer' ***
        return jsonify({"error": "Access forbidden. Only lecturers can change their password."}), 403 # 403 Forbidden


    # --- Get Password Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    required_fields = ['old_password', 'new_password']

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    old_password = data.get('old_password')
    new_password = data.get('new_password')

    # Basic validation for new password (e.g., minimum length) - optional but recommended
    if len(new_password) < 6: # Example: minimum 6 characters
        return jsonify({"error": "New password must be at least 6 characters long."}), 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- Verify Old Password ---
        # Fetch the current hashed password for the user account
        # *** VERIFY 'useraccounts' TABLE NAME AND 'user_account_id', 'hashed_password' COLUMNS ***
        cur.execute("SELECT password FROM useraccounts WHERE user_account_id = %s;", (user_account_id,))
        user_account = cur.fetchone()

        if user_account is None:
            # This case should ideally not be reached if token is valid, but good safeguard
            print(f"Error: User account not found for user_account_id {user_account_id} during lecturer password change.")
            return jsonify({"error": "User account not found."}), 404 # Or 401/500

        stored_hashed_password = user_account[0]

        # Use check_password_hash to compare the provided old password with the stored hash
        if not check_password_hash(stored_hashed_password, old_password):
            return jsonify({"error": "Incorrect old password."}), 401 # 401 Unauthorized


        # --- Hash the New Password ---
        hashed_new_password = generate_password_hash(new_password)


        # --- Update the Password in the Database ---
        sql_update_password = """
            UPDATE useraccounts -- *** Use the correct table name ***
            SET password = %s
            WHERE user_account_id = %s; -- Update the logged-in user's password
        """
        cur.execute(sql_update_password, (hashed_new_password, user_account_id))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if user_account was found, but safeguard
             return jsonify({"error": "Password could not be updated."}), 500


        conn.commit()

        return jsonify({"message": "Password updated successfully!"}), 200 # 200 OK

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer password change: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer password change: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/records/<record_id>', methods=['DELETE'])
@login_required # Apply the decorator to protect this route
def delete_lecturer_attendance_record(user, record_id):
    """
    Deletes a specific attendance record by record_id.
    Requires 'lecturer' role.
    Requires the record to belong to a session assigned to the logged-in lecturer.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can delete attendance records."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- Security Check: Verify the record exists and belongs to a session owned by the logged-in lecturer ---
        # Join attendancerecords to sessions and assignments to check ownership
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql_verify_record_ownership = """
            SELECT atr.record_id
            FROM attendancerecords atr -- Correct alias
            JOIN attendancesessions ats ON atr.session_id = ats.session_id -- Correct table names
            JOIN coursesassignedtolecturers cal ON ats.assignment_id = cal.assignment_id -- Correct table names
            WHERE atr.record_id = %s AND cal.lecturer_id = %s; -- Check record ID and logged-in lecturer ID
        """
        cur.execute(sql_verify_record_ownership, (record_id, lecturer_id))
        record_owner = cur.fetchone()

        if record_owner is None:
            # Record not found OR it does not belong to a session taught by this lecturer
            return jsonify({"error": "Attendance record not found or you do not have permission to delete it."}), 404 # Or 403


        # --- Delete the Attendance Record ---
        # No other tables reference attendance records, so direct deletion is fine
        sql_delete_record = "DELETE FROM attendancerecords WHERE record_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_record, (record_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if record_owner check passed
             return jsonify({"error": "Attendance record found but could not be deleted."}), 500


        conn.commit()
        return jsonify({"message": f"Attendance record {record_id} deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during lecturer attendance record deletion: {e}")
        # This shouldn't happen if no tables reference attendancerecords, but included for safety
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer attendance record deletion: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer attendance record deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/sessions/<session_id>/mark-present', methods=['POST'])
@login_required # Apply the decorator to protect this route
def mark_student_present_via_scan(user, session_id):
    """
    Marks a student as 'Present' for a specific session via QR code scan submission.
    Requires 'lecturer' role.
    Requires the session to be currently active and assigned to the logged-in lecturer.
    Accepts student_id in the JSON request body (parsed from scanned QR).
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id

    # --- Role Check ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can mark attendance."}), 403

    # --- Get Student ID from Request Body (from Scan) ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # Validate student_id is present and is a string
    student_id = data.get('student_id')
    if not student_id or not isinstance(student_id, str):
        return jsonify({"error": "Missing or invalid 'student_id' in request body."}), 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions

        # --- Step 1: Verify the Session Exists, Belongs to Lecturer, and Get Session Times ---
        # Need session_datetime and qr_code_expiry_time to check if scanning is allowed now
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES, CORRECTED ALIAS ***
        sql_get_session_details = """
            SELECT
                ats.session_id,
                ats.session_datetime,
                ats.qr_code_expiry_time,
                cal.course_id,        -- *** CORRECTED: Use alias 'cal' ***
                cal.academic_year_id  -- *** CORRECTED: Use alias 'cal' ***
            FROM attendancesessions ats -- Correct table name
            JOIN coursesassignedtolecturers cal ON ats.assignment_id = cal.assignment_id -- Correct table name
            WHERE ats.session_id = %s AND cal.lecturer_id = %s; -- Check session ID and logged-in lecturer ID
        """
        cur.execute(sql_get_session_details, (session_id, lecturer_id))
        session_details = cur.fetchone()

        if session_details is None:
            # Session not found OR it doesn't belong to this lecturer
            return jsonify({"error": "Attendance session not found or you do not have permission to mark attendance for it."}), 404 # Or 403

        # Extract session details - Access by index since using standard cursor
        fetched_session_id, session_datetime, qr_code_expiry_time, course_id, academic_year_id = session_details


        # --- Step 2: Check if the Session is Currently Active for Scanning ---
        # Compare current time to session_datetime and qr_code_expiry_time
        now = datetime.now(timezone.utc) # Get current time (make sure it's timezone-aware if DB is)

        # Check if now is between session_datetime and qr_code_expiry_time
        if not (session_datetime <= now <= qr_code_expiry_time):
             return jsonify({"error": "Attendance session is not currently active for scanning."}), 400 # 400 Bad Request

        # --- Step 3: Verify Student Exists and is Enrolled in This Course/Year ---
        # Check if student_id is a valid student AND is enrolled in the course/year of this session's assignment
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES ***
        sql_check_student_enrolled = """
            SELECT s.student_id
            FROM students s -- Correct table name
            JOIN studentsenrolledcourses sec ON s.student_id = sec.student_id -- Correct table name
            WHERE s.student_id = %s AND sec.course_id = %s AND sec.academic_year_id = %s; -- Check student ID and enrollment
        """
        cur.execute(sql_check_student_enrolled, (student_id, course_id, academic_year_id))
        student_enrolled = cur.fetchone()

        if student_enrolled is None:
            # Student not found OR student is not enrolled in this course/year
            return jsonify({"error": f"Student ID '{student_id}' is not enrolled in this course/year or does not exist."}), 400 # 400 Bad Request


        # --- Step 4: Create or Update Attendance Record ---
        # Check if an attendance record already exists for this student in this session
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES ***
        sql_check_existing_record = """
            SELECT record_id, status
            FROM attendancerecords -- Correct table name
            WHERE session_id = %s AND student_id = %s;
        """
        cur.execute(sql_check_existing_record, (session_id, student_id))
        existing_record = cur.fetchone()

        now_db = datetime.now(timezone.utc) # Get current time again for DB insertion/update timestamp

        if existing_record:
            # Record exists, maybe update the status to 'Present' if it's not already, and update attendance_time
            existing_record_id, current_status = existing_record
            if current_status != 'Present':
                 sql_update_record = """
                     UPDATE attendancerecords -- Correct table name
                     SET status = 'Present', attendance_time = %s -- Update status and time
                     WHERE record_id = %s;
                 """
                 cur.execute(sql_update_record, (now_db, existing_record_id))
                 action_taken = "updated (status changed to Present)"
            else:
                 # Record already exists and is 'Present', no update needed
                 action_taken = "already marked Present"

            message = f"Student '{student_id}' {action_taken} for session '{session_id}'."
            # Optional: Fetch and return the updated record details here

        else:
            # No record exists, create a new one with status 'Present'
            sql_create_record = """
                INSERT INTO attendancerecords (session_id, student_id, status, attendance_time) -- Correct columns
                VALUES (%s, %s, 'Present', %s) -- Set status to 'Present', use current time
                RETURNING record_id; -- Get the generated ID
            """
            cur.execute(sql_create_record, (session_id, student_id, now_db))
            new_record_id = cur.fetchone()[0]
            action_taken = "marked Present"
            message = f"Student '{student_id}' {action_taken} for session '{session_id}'. Record ID: {new_record_id}"
            # Optional: Fetch and return the new record details here


        conn.commit()

        return jsonify({"message": message}), 200 # 200 OK

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during attendance marking for session {session_id}, student {student_id}: {e}")
        return jsonify({"error": f"Database error during attendance marking: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance marking for session {session_id}, student {student_id}: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/profile', methods=['PUT'])
@login_required # Apply the decorator to protect this route
def update_lecturer_profile(user):
    """
    Allows the logged-in lecturer to update specific fields in their profile.
    Requires 'lecturer' role.
    Accepts the user tuple (user_account_id, role, entity_id) from the decorator.
    Accepts update data in the JSON request body.
    Only allows updates to a predefined set of fields.
    """
    user_account_id, role, lecturer_id = user # Unpack the user tuple; entity_id is the lecturer_id
    # Ensure lecturer_id is not None
    if lecturer_id is None:
         # This should be caught by login_required, but added as a safeguard
         return jsonify({"error": "Lecturer entity ID is missing in token."}), 401


    # --- Role Check: Ensure only lecturers can access this route ---
    if role != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can update their profile."}), 403 # 403 Forbidden


    # --- Get Update Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Define Allowed Fields for Lecturer Update ---
    # *** CAUTION: Be very selective here! ***
    # Only list fields from the 'lecturers' table that a lecturer should be allowed to change themselves.
    # Example: Contact number, email (if updating email here is desired/handled), perhaps address fields if they exist.
    # Do NOT include: lecturer_id, user_account_id, first_name, last_name, employee_id,
    # department_id, employment_date, date_of_birth, gender, etc.
    allowed_updatable_fields = [
        'contact_number',
        'email' # Include 'email' if it's in your 'lecturers' table and students can update it directly
        # Add other fields lecturers can update, like address fields (e.g., 'office_location')
        # if they exist in your lecturers table
    ]

    update_data = {}
    for field in allowed_updatable_fields:
        # Only include fields present in the request body (allow None or empty strings if nullable in schema)
        if field in data:
            update_data[field] = data[field]


    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No valid updatable fields provided in the request body."}), 200


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions

        # --- Optional Validation for Specific Fields ---
        # If you allow updating email, you might need format validation or a verification workflow
        # If you allow updating contact_number, you might add format validation here
        # Example: Basic email format check
        # if 'email' in update_data and update_data['email']:
        #      if not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', update_data['email']):
        #           return jsonify({"error": "Invalid email format."}), 400
        # Ensure 'import re' at the top if using regex validation

        # Example: Basic contact_number format check (simple - adjust regex as needed)
        # if 'contact_number' in update_data and update_data['contact_number']:
        #      # Assuming simple digits and hyphen format
        #      if not re.fullmatch(r'^\d[\d -]{7,15}$', update_data['contact_number']): # Basic check for 8-16 digits/spaces/hyphens
        #           return jsonify({"error": "Invalid contact number format."}), 400
        # Ensure 'import re' at the top if using regex validation


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No fields to set."}), 200 # Should be caught above


        sql_update = f"""
            UPDATE lecturers -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE lecturer_id = %s; -- Update the logged-in lecturer's record
        """
        # Pass values from update_data followed by the lecturer_id for the WHERE clause
        execute_values = list(update_data.values()) + [lecturer_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             # This might happen if lecturer_id from token doesn't match a record (shouldn't with safeguards)
             # or if the update data is exactly the same as current data.
             return jsonify({"message": "Lecturer profile found, but no changes were applied (data might be the same or no updatable fields provided)."}), 200


        conn.commit()

        # Optional: Re-fetch and return the updated profile details
        # You could call get_lecturer_profile(user) here or copy its fetch logic
        # For simplicity, just return a success message
        return jsonify({"message": "Lecturer profile updated successfully!"}), 200 # 200 OK

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during lecturer profile update: {e}")
        # Might happen if a unique constraint is violated (e.g., updating email if it's unique)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer profile update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer profile update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/lecturer/notifications', methods=['POST'])
@login_required # Protect this route
def create_notification_for_lecturer(user):
    """
    Creates a new notification via lecturer dashboard.
    Requires 'lecturer' role.
    Accepts notification data in JSON request body.
    Lecturers can only target 'Department' (their own) or 'Course' (they teach).
    """
    user_account_id_lecturer, role_lecturer, lecturer_id = user # Unpack the lecturer user tuple

    # --- Role Check: Ensure only lecturers can access this route ---
    if role_lecturer != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can create notifications."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    required_fields = ['title', 'message', 'target_role']

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    title = data.get('title')
    message = data.get('message')
    target_role = data.get('target_role')
    # Lecturers can't set these freely, they are determined by their role/teaching
    # We still extract them to ensure they are handled correctly (usually should be null)
    target_department_id_from_body = data.get('target_department_id')
    target_course_id_from_body = data.get('target_course_id')

    # --- Validate target_role for Lecturer ---
    allowed_target_roles_lecturer = ['Department', 'Course'] # Lecturers can only target these
    if target_role not in allowed_target_roles_lecturer:
        return jsonify({"error": f"Invalid target_role '{target_role}' for a lecturer. Allowed roles: {', '.join(allowed_target_roles_lecturer)}."}), 400

    # Initialize final IDs to be used for insertion
    final_target_department_id = None
    final_target_course_id = None

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # --- Handle Targeting Based on Lecturer's Role and Input ---
        if target_role == 'Department':
             # Get the lecturer's department ID
             # *** VERIFY 'lecturers' TABLE NAME AND 'lecturer_id', 'department_id' COLUMNS ***
             cur.execute("SELECT department_id FROM lecturers WHERE lecturer_id = %s;", (lecturer_id,))
             lecturer_dept_row = cur.fetchone()
             if lecturer_dept_row is None:
                  # This should ideally not happen if lecturer_id in useraccounts is correct
                  return jsonify({"error": "Lecturer's department not found."}), 500 # Or 400

             final_target_department_id = lecturer_dept_row[0] # Use the lecturer's actual department ID

             # Ensure course ID is null for Department target
             if target_course_id_from_body is not None:
                  return jsonify({"error": "target_course_id must be null for target_role 'Department' set by a lecturer."}), 400
             # Ensure department ID from body is null
             if target_department_id_from_body is not None:
                   return jsonify({"error": "target_department_id must be null in request body for target_role 'Department' set by a lecturer (it's determined by lecturer's department)."}), 400


        elif target_role == 'Course':
             if not target_course_id_from_body or not isinstance(target_course_id_from_body, str):
                  return jsonify({"error": "target_course_id is required and must be a string for target_role 'Course'."}), 400

             final_target_course_id = target_course_id_from_body

             # --- Security Check: Verify lecturer teaches this course ---
             # Check if the lecturer is assigned to an assignment for this course (in any academic year)
             # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'course_id', 'lecturer_id' COLUMNS ***
             sql_check_lecturer_teaches_course = """
                 SELECT assignment_id
                 FROM coursesassignedtolecturers -- Correct table name
                 WHERE course_id = %s AND lecturer_id = %s
                 LIMIT 1; -- Just need to know if at least one assignment exists
             """
             cur.execute(sql_check_lecturer_teaches_course, (final_target_course_id, lecturer_id))
             lecturer_teaches_course = cur.fetchone()

             if lecturer_teaches_course is None:
                  return jsonify({"error": f"You are not assigned to teach course ID '{final_target_course_id}' and cannot send a notification for it."}), 403 # Forbidden

             # Ensure department ID is null for Course target
             if target_department_id_from_body is not None:
                  return jsonify({"error": "target_department_id must be null for target_role 'Course' set by a lecturer."}), 400
             # Ensure course ID from body is the same as validated ID if provided (optional, redundant check)
             # if target_course_id_from_body != final_target_course_id:
             #      return jsonify({"error": "Mismatch between validated course ID and body course ID."}), 400


        # --- Ensure department_id and course_id are NOT set for other target roles (though validation above covers this) ---
        # This logic is implicitly handled by the target_role checks above


        # --- Create Notification Record ---
        # Insert into the notifications table
        # Exclude notification_id (generated by trigger/UUID)
        # Exclude created_at (has default)
        # *** VERIFY column names and order match your schema ***
        sql_insert_notification = """
            INSERT INTO notifications (title, message, created_by_user_account_id, target_role, target_department_id, target_course_id) -- *** Adjust column names ***
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING notification_id; -- Get the generated ID
        """
        execute_values = (
            title,
            message,
            user_account_id_lecturer, # Use the user_account_id from the logged-in lecturer
            target_role,
            final_target_department_id, # Use the determined department ID (lecturer's dept or null)
            final_target_course_id      # Use the determined course ID (teaches or null)
        )

        cur.execute(sql_insert_notification, execute_values)
        new_notification_id = cur.fetchone()[0]

        conn.commit()

        return jsonify({
            "message": f"Notification '{new_notification_id}' created successfully!",
            "notification_id": new_notification_id
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during lecturer notification creation: {e}")
        # This could happen due to FK violation if not caught by manual check or other constraints
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer notification creation: {e}")
        # This could happen if data types are wrong or other DB issues
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer notification creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/lecturer/notifications', methods=['GET'])
@login_required # Protect this route
def list_relevant_notifications_for_lecturer(user):
    """
    Retrieves a list of notifications relevant to the logged-in lecturer.
    Requires 'lecturer' role.
    """
    user_account_id_lecturer, role_lecturer, lecturer_id = user # Unpack the lecturer user tuple

    # --- Role Check: Ensure only lecturers can access this route ---
    if role_lecturer != 'lecturer':
        return jsonify({"error": "Access forbidden. Only lecturers can view their relevant notifications."}), 403

    conn = None
    cur = None
    notifications_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # --- Get Context for Filtering (Lecturer's Department and Taught Courses) ---
        # Fetch the lecturer's department ID
        # *** VERIFY 'lecturers' TABLE NAME AND 'lecturer_id', 'department_id' COLUMNS ***
        cur.execute("SELECT department_id FROM lecturers WHERE lecturer_id = %s;", (lecturer_id,))
        lecturer_dept_row = cur.fetchone()
        if lecturer_dept_row is None:
             # Should not happen if lecturer_id in useraccounts is correct
             print(f"Error: Lecturer department not found for lecturer_id {lecturer_id} during notification fetch.")
             return jsonify({"error": "Lecturer department not found."}), 500 # Or appropriate error

        lecturer_department_id = lecturer_dept_row['department_id'] # Get the department ID


        # Fetch the list of course IDs the lecturer is assigned to teach (in any year)
        # This is needed for filtering notifications targeted to courses they teach
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'lecturer_id', 'course_id' COLUMNS ***
        sql_get_lecturer_courses = """
            SELECT DISTINCT course_id
            FROM coursesassignedtolecturers -- Correct table name
            WHERE lecturer_id = %s; -- Filter by logged-in lecturer ID
        """
        cur.execute(sql_get_lecturer_courses, (lecturer_id,))
        lecturer_course_ids = [row['course_id'] for row in cur.fetchall()] # Get list of course IDs

        # Handle case where lecturer teaches no courses (empty list will work in SQL IN clause)
        if not lecturer_course_ids:
             # To ensure the IN clause works correctly even with an empty list,
             # use a condition that is always false if the list is empty.
             # We can add a placeholder like 'null' or an ID that won't match, or handle this in the WHERE clause logic.
             # The SQL query below uses the array syntax for IN which handles empty lists properly.
             pass # No specific action needed here


        # --- Fetch Relevant Notifications Data ---
        # Select notification details, joining useraccounts for creator info, and left joining
        # departments and courses for target names.
        # Apply the complex WHERE clause based on relevance rules for a lecturer.
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                n.notification_id,
                n.title,
                n.message,
                n.created_at,
                n.created_by_user_account_id,
                ua.username AS creator_username,
                ua.role AS creator_role,
                n.target_role,
                n.target_department_id,
                d.department_name AS target_department_name,
                n.target_course_id,
                c.course_code AS target_course_code,
                c.course_title AS target_course_title
            FROM notifications n
            JOIN useraccounts ua ON n.created_by_user_account_id = ua.user_account_id
            LEFT JOIN departments d ON n.target_department_id = d.department_id
            LEFT JOIN courses c ON n.target_course_id = c.course_id
            WHERE
                n.target_role = 'All' -- Targeted to everyone
                OR n.target_role = 'Lecturer' -- Targeted specifically to lecturers
                OR (n.target_role = 'Department' AND n.target_department_id = %s) -- Targeted to the lecturer's department
                OR (n.target_role = 'Course' AND n.target_course_id = ANY(%s::VARCHAR[])) -- Targeted to a course the lecturer teaches (use ANY with array)
                -- Optional: OR n.created_by_user_account_id = %s -- Show notifications created by this lecturer (redundant if they fall into other categories)
            ORDER BY n.created_at DESC;
        """
        # Pass parameters: lecturer_department_id, lecturer_course_ids (as a list/array), (optional: user_account_id_lecturer)
        # Use the ANY(array::VARCHAR[]) syntax for the IN clause with a list of IDs from Python.
        # Ensure the type cast ::VARCHAR[] matches your primary key type for course_id.

        # Execute the main query with the collected parameters
        cur.execute(sql, (lecturer_department_id, lecturer_course_ids)) # Add user_account_id_lecturer if showing own

        notifications_list = cur.fetchall()

        # Optional: Convert timestamps to string format for JSON if needed


        return jsonify(notifications_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching lecturer notifications: {e}")
        error_message = str(e)
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
            return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching lecturer notifications: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

######################################################################################################################################################

# --- Protected Admin Dashboard Routes ---
@app.route('/admin/students', methods=['GET'])
@login_required # Protect this route
def list_all_students(user):
    """
    Retrieves a list of all registered students.
    Requires 'admin' role.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the student list."}), 403


    # --- Fetch All Students Data ---
    conn = None
    cur = None
    students_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant student details, maybe join departments and useraccounts
        sql = """
            SELECT
                s.student_id,
                s.first_name,
                s.last_name,
                s.matriculation_number,
                s.level,
                s.intended_program,
                s.email,
                s.contact_number,
                s.date_of_birth,
                s.gender,
                s.admission_date,
                s.qr_code_data, -- Include QR data if needed for admin view
                d.department_name, -- Department name
                ua.username AS user_account_username -- Linked user account username
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            LEFT JOIN useraccounts ua ON s.user_account_id = ua.user_account_id -- LEFT JOIN in case a student record exists without a user account (less likely now)
            ORDER BY s.admission_date DESC, s.last_name, s.first_name; -- Order by admission date, then name
        """
        # No WHERE clause needed to filter by a specific user ID, as admin sees all
        cur.execute(sql)

        students_list = cur.fetchall()

        return jsonify(students_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching student list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching student list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/lecturers', methods=['GET'])
@login_required # Protect this route
def list_all_lecturers(user):
    """
    Retrieves a list of all registered lecturers.
    Requires 'admin' role.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the lecturer list."}), 403


    # --- Fetch All Lecturers Data ---
    conn = None
    cur = None
    lecturers_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant lecturer details, maybe join departments and useraccounts
        sql = """
            SELECT
                l.lecturer_id, -- Primary key for lecturer
                l.first_name,
                l.last_name,
                l.employee_id, -- Employee ID for lecturer
                l.email,
                l.contact_number,
                l.date_of_employment,
                d.department_name, -- Department name
                ua.username AS user_account_username -- Linked user account username
            FROM lecturers l
            JOIN departments d ON l.department_id = d.department_id
            LEFT JOIN useraccounts ua ON l.user_account_id = ua.user_account_id -- LEFT JOIN in case a lecturer record exists without a user account
            ORDER BY l.date_of_employment DESC, l.last_name, l.first_name; -- Order by employment date, then name
        """
        # No WHERE clause needed to filter by a specific user ID, as admin sees all
        cur.execute(sql)

        lecturers_list = cur.fetchall()

        return jsonify(lecturers_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching lecturer list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching lecturer list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/students/<student_id>', methods=['GET'])
@login_required # Protect this route
def get_student_details_for_admin(user, student_id):
    """
    Retrieves details of a specific student by student_id for admin view.
    Requires 'admin' role.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view student details."}), 403


    # --- Fetch Specific Student Data ---
    conn = None
    cur = None
    student_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant student details for the given student_id
        sql = """
            SELECT
                s.student_id,
                s.first_name,
                s.last_name,
                s.matriculation_number,
                s.level,
                s.intended_program,
                s.email,
                s.contact_number,
                s.date_of_birth,
                s.gender,
                s.admission_date,
                s.qr_code_data,
                d.department_name,
                ua.username AS user_account_username
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            LEFT JOIN useraccounts ua ON s.user_account_id = ua.user_account_id
            WHERE s.student_id = %s; -- *** Filter by the student_id from the URL path ***
        """
        # Use the student_id from the URL path parameter
        cur.execute(sql, (student_id,))

        student_details = cur.fetchone()

        if student_details is None:
            # Student with the given ID not found
            return jsonify({"error": "Student not found."}), 404 # 404 Not Found

        return jsonify(student_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific student details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific student details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/lecturers/<lecturer_id>', methods=['GET'])
@login_required # Protect this route
def get_lecturer_details_for_admin(user, lecturer_id):
    """
    Retrieves details of a specific lecturer by lecturer_id for admin view.
    Requires 'admin' role.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view lecturer details."}), 403


    # --- Fetch Specific Lecturer Data ---
    conn = None
    cur = None
    lecturer_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant lecturer details for the given lecturer_id
        # Join departments and useraccounts for related info
        sql = """
            SELECT
                l.lecturer_id,
                l.first_name,
                l.last_name,
                l.employee_id,
                l.email,
                l.contact_number,
                l.date_of_employment,
                d.department_name,
                ua.username AS user_account_username
            FROM lecturers l
            JOIN departments d ON l.department_id = d.department_id
            LEFT JOIN useraccounts ua ON l.user_account_id = ua.user_account_id
            WHERE l.lecturer_id = %s; -- *** Filter by the lecturer_id from the URL path ***
        """
        # Use the lecturer_id from the URL path parameter
        cur.execute(sql, (lecturer_id,))

        lecturer_details = cur.fetchone()

        if lecturer_details is None:
            # Lecturer with the given ID not found
            return jsonify({"error": "Lecturer not found."}), 404 # 404 Not Found

        return jsonify(lecturer_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific lecturer details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific lecturer details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/students/<student_id>', methods=['PUT'])
@login_required # Protect this route
def update_student_details_for_admin(user, student_id):
    """
    Updates details of a specific student by student_id for admin view.
    Requires 'admin' role.
    Accepts updated student data in JSON request body.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update student details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # Extract fields that are allowed to be updated by admin
    # You can add or remove fields based on what you want admins to edit
    # Note: Typically primary keys (student_id), linked user_account_id are NOT updated here.
    updatable_fields = [
        'first_name', 'last_name', 'matriculation_number', 'level',
        'intended_program', 'email', 'contact_number', 'date_of_birth',
        'gender', 'admission_date', 'department_id' # department_id should be a valid FK
        # QR code data might be regenerated or handled differently
    ]
    update_data = {}
    for field in updatable_fields:
        if field in data:
            update_data[field] = data[field]

    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # <--- Change it to this

        # --- First, verify if the student exists ---
        cur.execute("SELECT student_id FROM students WHERE student_id = %s;", (student_id,))
        student_exists = cur.fetchone()
        if student_exists is None:
            return jsonify({"error": "Student not found."}), 404


        # --- Construct and Execute the UPDATE SQL Query ---
        # Build the SET part of the SQL query dynamically based on update_data
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
            # Should be caught by the earlier check, but as a safeguard
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE students
            SET {', '.join(set_clauses)}
            WHERE student_id = %s;
        """
        # The values for the execute tuple are the values from update_data
        # followed by the student_id for the WHERE clause
        execute_values = list(update_data.values()) + [student_id]

        cur.execute(sql_update, execute_values)

        # Check if any rows were affected
        if cur.rowcount == 0:
            # This might happen if the student_id was valid but no changes were made (should be rare with previous check)
            # Or if something prevented the update (e.g., invalid department_id not caught earlier)
            # Depending on desired strictness, you might return a different status.
             return jsonify({"message": "Student found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated student details or a success message
        # Fetching updated details is more informative for the frontend
        cur.execute(
             """
            SELECT
                s.student_id, s.first_name, s.last_name, s.matriculation_number, s.level, s.intended_program,
                s.email, s.contact_number, s.date_of_birth, s.gender, s.admission_date, s.qr_code_data,
                d.department_name, ua.username AS user_account_username
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            LEFT JOIN useraccounts ua ON s.user_account_id = ua.user_account_id
            WHERE s.student_id = %s;
            """, (student_id,))
        updated_student_details = cur.fetchone()


        return jsonify(updated_student_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during student update: {e}")
        # This could happen if department_id is invalid or matriculation_number is not unique
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during student update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during student update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/lecturers/<lecturer_id>', methods=['PUT'])
@login_required # Protect this route
def update_lecturer_details_for_admin(user, lecturer_id):
    """
    Updates details of a specific lecturer by lecturer_id for admin view.
    Requires 'admin' role.
    Accepts updated lecturer data in JSON request body.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update lecturer details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # Extract fields that are allowed to be updated by admin
    # Adjust these fields based on what you want admins to edit in the lecturers table
    updatable_fields = [
        'first_name', 'last_name', 'employee_id', 'email',
        'contact_number', 'date_of_employment', 'department_id' # department_id should be a valid FK
    ]
    update_data = {}
    for field in updatable_fields:
        if field in data:
            update_data[field] = data[field]

    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor

        # --- First, verify if the lecturer exists ---
        cur.execute("SELECT lecturer_id FROM lecturers WHERE lecturer_id = %s;", (lecturer_id,))
        lecturer_exists = cur.fetchone()
        if lecturer_exists is None:
            return jsonify({"error": "Lecturer not found."}), 404


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE lecturers
            SET {', '.join(set_clauses)}
            WHERE lecturer_id = %s;
        """
        execute_values = list(update_data.values()) + [lecturer_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Lecturer found, but no changes were applied."}), 200


        conn.commit()
        # Return the updated lecturer details
        cur.execute(
             """
            SELECT
                l.lecturer_id, l.first_name, l.last_name, l.employee_id, l.email, l.contact_number,
                l.date_of_employment, d.department_name, ua.username AS user_account_username
            FROM lecturers l
            JOIN departments d ON l.department_id = d.department_id
            LEFT JOIN useraccounts ua ON l.user_account_id = ua.user_account_id
            WHERE l.lecturer_id = %s;
            """, (lecturer_id,))
        updated_lecturer_details = cur.fetchone()


        return jsonify(updated_lecturer_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during lecturer update: {e}")
        # This could happen if department_id is invalid or employee_id is not unique (if it has a unique constraint)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/students/<student_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_student_for_admin(user, student_id):
    """
    Deletes a specific student by student_id for admin view,
    including associated records, handling FK constraints with NO ACTION.
    Requires 'admin' role.
    """
    user_account_id, role, entity_id = user # Unpack the user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete students."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # --- First, verify if the student exists and get linked user_account_id ---
        # Use a standard cursor here
        cur.execute("SELECT student_id, user_account_id FROM students WHERE student_id = %s;", (student_id,))
        student_row = cur.fetchone()
        if student_row is None:
            return jsonify({"error": "Student not found."}), 404

        linked_user_account_id = student_row[1] # Get the linked user_account_id


        # --- Delete Related Records (Order is crucial with NO ACTION!) ---

        # 1. Delete Attendance Records (references students)
        sql_delete_attendance = "DELETE FROM attendancerecords WHERE student_id = %s;"
        cur.execute(sql_delete_attendance, (student_id,))
        print(f"Deleted {cur.rowcount} attendance records for student {student_id}") # Debug print

        # 2. Delete Student Course Enrollments (references students)
        # Use the correct table name (studentsenrolledcourses) and column name (student_id or student_id)
        # *** CRITICAL VERIFICATION: DOUBLE CHECK YOUR TABLE AND COLUMN NAME HERE ***
        sql_delete_enrollments = "DELETE FROM studentsenrolledcourses WHERE student_id = %s;" # <--- VERIFY 'student_id' vs 'student_id'
        cur.execute(sql_delete_enrollments, (student_id,))
        print(f"Deleted {cur.rowcount} enrollment records for student {student_id}") # Debug print

        # --- 3. IMPORTANT: Set the student's user_account_id to NULL (referenced by students table) ---
        # This must happen before deleting the user account if FK has NO ACTION
        sql_set_user_account_null = "UPDATE students SET user_account_id = NULL WHERE student_id = %s;"
        cur.execute(sql_set_user_account_null, (student_id,))
        print(f"Set students.user_account_id to NULL for student {student_id}") # Debug print

        # 4. Delete the linked User Account (if one exists)
        # This can now be done because the student record no longer references it
        if linked_user_account_id:
            sql_delete_user = "DELETE FROM useraccounts WHERE user_account_id = %s;"
            cur.execute(sql_delete_user, (linked_user_account_id,))
            print(f"Deleted user account {linked_user_account_id} linked to student {student_id}") # Debug print


        # --- 5. Finally, Delete the Student Record (can now be done as referencing records are gone/nulled) ---
        sql_delete_student = "DELETE FROM students WHERE student_id = %s;"
        cur.execute(sql_delete_student, (student_id,))

        # Check if the student record was actually deleted
        if cur.rowcount == 0:
             # Should ideally not happen if student_exists check passed, but good practice
             if conn:
                 conn.rollback() # Rollback if the final delete failed unexpectedly
             return jsonify({"error": "Student found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Student {student_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during student deletion: {e}")
        # If you still get a foreign key violation here, it means a referencing table wasn't handled or order is wrong!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during student deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/lecturers/<lecturer_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_lecturer_for_admin(user, lecturer_id):
    """
    Deletes a specific lecturer by lecturer_id for admin view,
    including associated records, handling FK constraints with NO ACTION.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete lecturers."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the lecturer exists and get linked user_account_id ---
        cur.execute("SELECT lecturer_id, user_account_id FROM lecturers WHERE lecturer_id = %s;", (lecturer_id,))
        lecturer_row = cur.fetchone()
        if lecturer_row is None:
            return jsonify({"error": "Lecturer not found."}), 404

        linked_user_account_id = lecturer_row[1] # Get the linked user_account_id


        # --- Delete Related Records (Order is crucial with NO ACTION!) ---

        # 1. Find all assignment_ids for this lecturer
        sql_get_assignments = """
            SELECT assignment_id FROM coursesassignedtolecturers WHERE lecturer_id = %s;
        """
        cur.execute(sql_get_assignments, (lecturer_id,))
        assignment_ids_rows = cur.fetchall()
        assignment_ids = [row[0] for row in assignment_ids_rows]
        print(f"Found {len(assignment_ids)} assignments for lecturer {lecturer_id}: {assignment_ids}") # Debug print


        # 2. If assignments exist, find all session_ids for these assignments
        session_ids = []
        if assignment_ids:
            sql_get_sessions = """
                SELECT session_id FROM attendancesessions WHERE assignment_id IN %s;
            """
            cur.execute(sql_get_sessions, (tuple(assignment_ids),))
            session_ids_rows = cur.fetchall()
            session_ids = [row[0] for row in session_ids_rows]
            print(f"Found {len(session_ids)} sessions for assignments: {session_ids}") # Debug print

            # 3. If sessions exist, delete attendance records for these sessions
            if session_ids:
                sql_delete_attendance = """
                    DELETE FROM attendancerecords WHERE session_id IN %s;
                """
                cur.execute(sql_delete_attendance, (tuple(session_ids),))
                print(f"Deleted {cur.rowcount} attendance records for sessions") # Debug print

            # 4. Delete the sessions themselves (if sessions exist)
            sql_delete_sessions = """
                DELETE FROM attendancesessions WHERE assignment_id IN %s;
            """
            cur.execute(sql_delete_sessions, (tuple(assignment_ids),))
            print(f"Deleted {cur.rowcount} sessions for assignments") # Debug print


        # 5. Delete the course assignments for this lecturer
        sql_delete_assignments = "DELETE FROM coursesassignedtolecturers WHERE lecturer_id = %s;"
        cur.execute(sql_delete_assignments, (lecturer_id,))
        print(f"Deleted {cur.rowcount} assignments for lecturer {lecturer_id}") # Debug print

        # --- 6. IMPORTANT: Set the lecturer's user_account_id to NULL ---
        # This must happen before deleting the user account because lecturers.user_account_id FK to useraccounts.user_account_id
        sql_set_user_account_null = "UPDATE lecturers SET user_account_id = NULL WHERE lecturer_id = %s;"
        cur.execute(sql_set_user_account_null, (lecturer_id,))
        print(f"Set lecturers.user_account_id to NULL for lecturer {lecturer_id}") # Debug print

        # 7. Delete the linked User Account (if one exists)
        # This can now be done because the lecturer record no longer references it
        if linked_user_account_id:
            sql_delete_user = "DELETE FROM useraccounts WHERE user_account_id = %s;"
            cur.execute(sql_delete_user, (linked_user_account_id,))
            print(f"Deleted user account {linked_user_account_id} linked to lecturer {lecturer_id}") # Debug print


        # --- 8. Finally, Delete the Lecturer Record ---
        sql_delete_lecturer = "DELETE FROM lecturers WHERE lecturer_id = %s;"
        cur.execute(sql_delete_lecturer, (lecturer_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Lecturer found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Lecturer {lecturer_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer deletion: {e}")
        # If you still get a foreign key violation here, it means a referencing table wasn't handled or order is wrong!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/students', methods=['POST'])
@login_required # Protect this route
def create_student_for_admin(user):
    """
    Creates a new student and linked user account via admin dashboard.
    Requires 'admin' role.
    Accepts new student/user data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create students."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Define the fields required to create a new student and their user account
    required_fields = [
        'first_name', 'last_name', 'email', 'contact_number', 'date_of_birth',
        'gender', 'level', 'intended_program', 'department_id', 'matriculation_number',
        'academic_year_id', 'proposed_username', 'proposed_password' # User account details
    ]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    contact_number = data.get('contact_number')
    date_of_birth = data.get('date_of_birth')
    gender = data.get('gender')
    level = data.get('level')
    intended_program = data.get('intended_program')
    department_id = data.get('department_id') # FK to departments
    matriculation_number = data.get('matriculation_number') # Should be unique
    academic_year_id = data.get('academic_year_id') # FK to academicyears
    proposed_username = data.get('proposed_username') # Should be unique in useraccounts
    proposed_password = data.get('proposed_password')


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation (More robust validation needed in a real app) ---
        # You might want to check for duplicate matriculation_number or username here
        # Or validate department_id and academic_year_id FK existence before insert

        # Check for duplicate matriculation number
        cur.execute("SELECT student_id FROM students WHERE matriculation_number = %s;", (matriculation_number,))
        if cur.fetchone():
             return jsonify({"error": f"Matriculation number {matriculation_number} already exists."}), 409 # 409 Conflict

        # Check for duplicate username
        cur.execute("SELECT user_account_id FROM useraccounts WHERE username = %s;", (proposed_username,))
        if cur.fetchone():
             return jsonify({"error": f"Username '{proposed_username}' already exists."}), 409 # 409 Conflict


        # --- Hash the password ---
        hashed_password = generate_password_hash(proposed_password) # Use werkzeug security

        # --- Create User Account ---
        # We insert into useraccounts first to get the user_account_id
        # useraccounts.entity_id will be NULL initially for a student until student record is created
        # Make sure useraccounts.entity_id is NULLABLE!
        sql_insert_user = """
            INSERT INTO useraccounts (username, password, role, entity_id)
            VALUES (%s, %s, %s, NULL) -- entity_id is NULL initially
            RETURNING user_account_id;
        """
        cur.execute(sql_insert_user, (proposed_username, hashed_password, 'student'))
        new_user_account_id = cur.fetchone()[0]


        # --- Create Student Record ---
        # Insert into the students table, linking the user_account_id
        # Make sure students.user_account_id is NULLABLE!
        sql_insert_student = """
            INSERT INTO students (first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_program, department_id, matriculation_number, academic_year_id, user_account_id, admission_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) -- Link user_account_id here
            RETURNING student_id;
        """
        cur.execute(sql_insert_student, (
             first_name, last_name, email, contact_number, date_of_birth, gender, level, intended_program,
             department_id, matriculation_number, academic_year_id, new_user_account_id # Link the user account ID
        ))
        new_student_id = cur.fetchone()[0]


        # --- Update User Account with Entity ID ---
        # Now that we have the student_id, update the user account's entity_id
        sql_update_user_entity = """
            UPDATE useraccounts
            SET entity_id = %s
            WHERE user_account_id = %s;
        """
        cur.execute(sql_update_user_entity, (new_student_id, new_user_account_id))


        # --- Generate and Update QR Code Data String ---
        # Need to refetch data to generate QR code string properly
        # Switch cursor to RealDictCursor temporarily to get data by name
        cur_dict = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur_dict.execute(
             """
            SELECT
                s.student_id, s.first_name, s.last_name, s.matriculation_number, s.level,
                d.department_name
            FROM students s
            JOIN departments d ON s.department_id = d.department_id
            WHERE s.student_id = %s;
            """, (new_student_id,))
        new_student_details_for_qr = cur_dict.fetchone()
        cur_dict.close() # Close the temporary cursor

        qr_data_string = None
        if new_student_details_for_qr:
             qr_data_string = generate_student_qr_data_string_from_dict(new_student_details_for_qr) # Use helper function
             if qr_data_string:
                sql_update_qr = "UPDATE students SET qr_code_data = %s WHERE student_id = %s;"
                cur.execute(sql_update_qr, (qr_data_string, new_student_id))
             else:
                 print(f"Warning: qr_data_string is None. Could not generate QR data string for new student_id {new_student_id}. qr_code_data column will be NULL.")
        else:
             print(f"Warning: Could not refetch student details for QR code generation for student_id {new_student_id}.")


        conn.commit()

        # Optional: Fetch and return the full details of the newly created student
        # Reuse the GET /admin/students/<student_id> logic or query again
        # Using the GET logic is cleaner if it's already tested and working
        # For simplicity now, let's return a success message and the new IDs

        return jsonify({
            "message": f"Student {first_name} {last_name} created successfully!",
            "student_id": new_student_id,
            "user_account_id": new_user_account_id,
            "username": proposed_username,
            "qr_code_data": qr_data_string # Include generated QR data
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during student creation: {e}")
        # This could happen due to duplicate matriculation_number, username, or invalid FKs
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during student creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during student creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        # Ensure temporary cursor is closed if used
        # if 'cur_dict' in locals() and cur_dict:
        #     cur_dict.close()
        if conn:
            conn.close()

def generate_student_qr_data_string_from_dict(student_data_dict):
    """Generates QR data string from a student details dictionary."""
    if not student_data_dict:
        return None
    # Ensure all expected keys are present, use get with default None
    student_id = student_data_dict.get('student_id', '')
    first_name = student_data_dict.get('first_name', '')
    last_name = student_data_dict.get('last_name', '')
    matriculation_number = student_data_dict.get('matriculation_number', '')
    level = student_data_dict.get('level', '')
    department_name = student_data_dict.get('department_name', '')

    # Basic format, adapt as needed
    qr_data = f"ID:{student_id},Name:{first_name} {last_name},Matric:{matriculation_number},Level:{level},Dept:{department_name}"
    return qr_data

####################################################################################

@app.route('/admin/lecturers', methods=['POST'])
@login_required # Protect this route
def create_lecturer_for_admin(user):
    """
    Creates a new lecturer and linked user account via admin dashboard.
    Requires 'admin' role.
    Accepts new lecturer/user data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create lecturers."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Define the fields required to create a new lecturer and their user account
    required_fields = [
        'first_name', 'last_name', 'email', 'contact_number', 'employee_id',
        'department_id', 'proposed_username', 'proposed_password' # User account details
        # date_of_employment might default to NOW()
    ]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    contact_number = data.get('contact_number')
    employee_id = data.get('employee_id') # Should be unique
    department_id = data.get('department_id') # FK to departments
    proposed_username = data.get('proposed_username') # Should be unique in useraccounts
    proposed_password = data.get('proposed_password')
    # date_of_employment will use NOW() default


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate employee_id or username
        cur.execute("SELECT lecturer_id FROM lecturers WHERE employee_id = %s;", (employee_id,))
        if cur.fetchone():
             return jsonify({"error": f"Employee ID {employee_id} already exists."}), 409 # 409 Conflict

        cur.execute("SELECT user_account_id FROM useraccounts WHERE username = %s;", (proposed_username,))
        if cur.fetchone():
             return jsonify({"error": f"Username '{proposed_username}' already exists."}), 409 # 409 Conflict

        # Check if department_id is valid (optional but recommended)
        # cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (department_id,))
        # if not cur.fetchone():
        #     return jsonify({"error": f"Department ID '{department_id}' not found."}), 400


        # --- Hash the password ---
        hashed_password = generate_password_hash(proposed_password)

        # --- Create User Account ---
        # Insert into useraccounts first to get the user_account_id
        # useraccounts.entity_id will be NULL initially for a lecturer until lecturer record is created
        # Make sure useraccounts.entity_id is NULLABLE!
        sql_insert_user = """
            INSERT INTO useraccounts (username, password, role, entity_id)
            VALUES (%s, %s, %s, NULL) -- entity_id is NULL initially
            RETURNING user_account_id;
        """
        cur.execute(sql_insert_user, (proposed_username, hashed_password, 'lecturer'))
        new_user_account_id = cur.fetchone()[0]


        # --- Create Lecturer Record ---
        # Insert into the lecturers table, linking the user_account_id
        # Make sure lecturers.user_account_id is NULLABLE!
        # lecturer_id (PK) might be generated automatically
        sql_insert_lecturer = """
            INSERT INTO lecturers (first_name, last_name, email, contact_number, employee_id, department_id, user_account_id, date_of_employment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) -- Link user_account_id here
            RETURNING lecturer_id; -- Assuming lecturer_id is the PK and is returned
        """
        cur.execute(sql_insert_lecturer, (
             first_name, last_name, email, contact_number, employee_id,
             department_id, new_user_account_id # Link the user account ID
        ))
        new_lecturer_id = cur.fetchone()[0]


        # --- Update User Account with Entity ID ---
        # Now that we have the lecturer_id, update the user account's entity_id
        sql_update_user_entity = """
            UPDATE useraccounts
            SET entity_id = %s
            WHERE user_account_id = %s;
        """
        cur.execute(sql_update_user_entity, (new_lecturer_id, new_user_account_id))


        conn.commit()

        # Optional: Fetch and return the full details of the newly created lecturer
        # Using the GET /admin/lecturers/<lecturer_id> logic is cleaner
        # For simplicity now, let's return a success message and the new IDs

        return jsonify({
            "message": f"Lecturer {first_name} {last_name} created successfully!",
            "lecturer_id": new_lecturer_id,
            "user_account_id": new_user_account_id,
            "username": proposed_username,
            "employee_id": employee_id # Include employee_id as it's often used
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during lecturer creation: {e}")
        # This could happen due to duplicate employee_id, username, or invalid FKs
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during lecturer creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during lecturer creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admins', methods=['POST'])
@login_required # Protect this route
def create_admin_for_admin(user):
    """
    Creates a new admin user and linked admin record via admin dashboard.
    Requires 'admin' role.
    Accepts new admin/user data in JSON request body.
    """
    user_account_id_admin_requester, role_admin_requester, entity_id_admin_requester = user # Unpack the admin user making the request

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create other admins."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    required_fields = [
        'first_name', 'last_name', 'email', 'contact_number',
        'employee_id', # Employee/Admin ID - should be unique in administrators
        'proposed_username', 'proposed_password'
    ]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    contact_number = data.get('contact_number')
    employee_id = data.get('employee_id')
    proposed_username = data.get('proposed_username')
    proposed_password = data.get('proposed_password')


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- Basic Validation ---
        # Check for duplicate employee_id in administrators table
        # *** CORRECTED TABLE NAME ***
        sql_check_employee_id = "SELECT admin_id FROM administrators WHERE employee_id = %s;"
        cur.execute(sql_check_employee_id, (employee_id,))
        if cur.fetchone():
             return jsonify({"error": f"Employee ID {employee_id} already exists in administrators."}), 409

        # Check for duplicate username in useraccounts table
        sql_check_username = "SELECT user_account_id FROM useraccounts WHERE username = %s;"
        cur.execute(sql_check_username, (proposed_username,))
        if cur.fetchone():
             return jsonify({"error": f"Username '{proposed_username}' already exists."}), 409


        # --- Hash the password ---
        hashed_password = generate_password_hash(proposed_password)

        # --- Create User Account ---
        sql_insert_user = """
            INSERT INTO useraccounts (username, password, role, entity_id)
            VALUES (%s, %s, %s, NULL) -- entity_id is NULL initially
            RETURNING user_account_id;
        """
        cur.execute(sql_insert_user, (proposed_username, hashed_password, 'admin'))
        new_user_account_id = cur.fetchone()[0]


        # --- Create Admin Record ---
        # *** CORRECTED TABLE NAME ***
        sql_insert_admin = """
            INSERT INTO administrators (first_name, last_name, email, contact_number, employee_id, user_account_id) -- *** CORRECTED: Table name and removed date_of_employment ***
            VALUES (%s, %s, %s, %s, %s, %s) -- *** CORRECTED: 6 placeholders ***
            RETURNING admin_id; -- *** Assuming admin_id is the PK and is returned ***
        """
        cur.execute(sql_insert_admin, (
             first_name, last_name, email, contact_number, employee_id,
             new_user_account_id # 6 values matching placeholders
        ))
        new_admin_id = cur.fetchone()[0]


        # --- Update User Account with Entity ID ---
        sql_update_user_entity = """
            UPDATE useraccounts
            SET entity_id = %s
            WHERE user_account_id = %s;
        """
        cur.execute(sql_update_user_entity, (new_admin_id, new_user_account_id))


        conn.commit()

        return jsonify({
            "message": f"Admin user '{proposed_username}' created successfully!",
            "admin_id": new_admin_id,
            "user_account_id": new_user_account_id,
            "username": proposed_username,
            "employee_id": employee_id
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during admin creation: {e}")
        # Check for specific error messages related to unique constraints or FKs
        if "unique constraint" in str(e).lower() or "duplicate key value" in str(e).lower():
             return jsonify({"error": "Integrity error: Duplicate employee ID or username."}), 409
        # Generic integrity error for other cases like invalid FKs
        return jsonify({"error": f"Database integrity error: {e}"}), 409

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during admin creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during admin creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admins', methods=['GET'])
@login_required # Protect this route
def list_all_admins(user):
    """
    Retrieves a list of all registered administrators.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the admin list."}), 403


    # --- Fetch All Admins Data ---
    conn = None
    cur = None
    admins_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant admin details, join useraccounts
        # *** CORRECTED: Removed date_of_employment column ***
        sql = """
            SELECT
                a.admin_id, -- Primary key for admin
                a.first_name,
                a.last_name,
                a.employee_id, -- Employee ID for admin
                a.email,
                a.contact_number,
                ua.username AS user_account_username -- Linked user account username
            FROM administrators a -- Use the correct table name
            LEFT JOIN useraccounts ua ON a.user_account_id = ua.user_account_id
            ORDER BY a.last_name, a.first_name; -- Order by name (removed date_of_employment from order if it was there)
        """
        # The ORDER BY in the original code didn't include date_of_employment, so it's fine.

        cur.execute(sql)

        admins_list = cur.fetchall()

        return jsonify(admins_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching admin list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching admin list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admins/<admin_id>', methods=['GET'])
@login_required # Protect this route
def get_admin_details_for_admin(user, admin_id):
    """
    Retrieves details of a specific administrator by admin_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view admin details."}), 403


    # --- Fetch Specific Admin Data ---
    conn = None
    cur = None
    admin_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant admin details for the given admin_id
        # Join useraccounts for linked username
        # *** VERIFY 'administrators' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                a.admin_id, -- Primary key
                a.first_name,
                a.last_name,
                a.employee_id,
                a.email,
                a.contact_number,
                a.date_of_employment, -- Check if this column exists based on previous findings (likely remove)
                ua.username AS user_account_username
            FROM administrators a -- *** Use the correct table name ***
            LEFT JOIN useraccounts ua ON a.user_account_id = ua.user_account_id
            WHERE a.admin_id = %s; -- *** Filter by the admin_id from the URL path ***
        """
        # Note: Based on the previous error, date_of_employment might not exist in 'administrators'.
        # If it doesn't exist, remove a.date_of_employment from the SELECT list.
        # If it exists, keep it. Remove it based on the last error.

        # Corrected SQL based on previous error (removing date_of_employment)
        sql = """
            SELECT
                a.admin_id,
                a.first_name,
                a.last_name,
                a.employee_id,
                a.email,
                a.contact_number,
                ua.username AS user_account_username
            FROM administrators a
            LEFT JOIN useraccounts ua ON a.user_account_id = ua.user_account_id
            WHERE a.admin_id = %s;
        """

        # Use the admin_id from the URL path parameter
        cur.execute(sql, (admin_id,))

        admin_details = cur.fetchone()

        if admin_details is None:
            # Admin with the given ID not found
            return jsonify({"error": "Administrator not found."}), 404 # 404 Not Found

        return jsonify(admin_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific admin details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific admin details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admins/<admin_id>', methods=['PUT'])
@login_required # Protect this route
def update_admin_details_for_admin(user, admin_id):
    """
    Updates details of a specific administrator by admin_id for admin view.
    Requires 'admin' role.
    Accepts updated admin data in JSON request body.
    """
    user_account_id_admin_requester, role_admin_requester, entity_id_admin_requester = user # Unpack the requesting admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update admin details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # You can add or remove fields based on what you want admins to edit
    # Note: Typically primary keys (admin_id), linked user_account_id are NOT updated here.
    # employee_id might or might not be updatable
    updatable_fields = [
        'first_name', 'last_name', 'employee_id', 'email',
        'contact_number'
        # date_of_employment was found to be non-existent, so exclude
    ]
    update_data = {}
    for field in updatable_fields:
        if field in data:
            update_data[field] = data[field]

    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor

        # --- First, verify if the administrator exists ---
        # *** VERIFY 'administrators' TABLE NAME AND 'admin_id' COLUMN ***
        cur.execute("SELECT admin_id FROM administrators WHERE admin_id = %s;", (admin_id,))
        admin_exists = cur.fetchone()
        if admin_exists is None:
            return jsonify({"error": "Administrator not found."}), 404


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE administrators -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE admin_id = %s; -- *** Filter by the admin_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [admin_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Administrator found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated administrator details
        # Reuse the GET /admin/admins/<admin_id> logic
        cur.execute(
             """
            SELECT
                a.admin_id, a.first_name, a.last_name, a.employee_id, a.email, a.contact_number,
                ua.username AS user_account_username
            FROM administrators a
            LEFT JOIN useraccounts ua ON a.user_account_id = ua.user_account_id
            WHERE a.admin_id = %s;
            """, (admin_id,))
        updated_admin_details = cur.fetchone()


        return jsonify(updated_admin_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during admin update: {e}")
        # This could happen if employee_id is not unique (if allowed to update)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during admin update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during admin update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admins/<admin_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_admin_for_admin(user, admin_id):
    """
    Deletes a specific administrator by admin_id for admin view,
    including associated records based on ON DELETE NO ACTION schema.
    Requires 'admin' role.
    Does NOT prevent deleting the last admin (implement safeguard in production).
    """
    user_account_id_admin_requester, role_admin_requester, entity_id_admin_requester = user # Unpack the requesting admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete other administrators."}), 403

    # --- Prevent deleting self (basic safeguard) ---
    if entity_id_admin_requester == admin_id:
         return jsonify({"error": "You cannot delete your own administrator account."}), 400 # Or 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the administrator exists and get linked user_account_id ---
        # *** VERIFY 'administrators' TABLE NAME AND 'admin_id', 'user_account_id' COLUMNS ***
        cur.execute("SELECT admin_id, user_account_id FROM administrators WHERE admin_id = %s;", (admin_id,))
        admin_row = cur.fetchone()
        if admin_row is None:
            return jsonify({"error": "Administrator not found."}), 404

        linked_user_account_id = admin_row[1] # Get the linked user_account_id


        # --- Delete/Update Related Records (Order is crucial with NO ACTION!) ---

        # 1. Set FKs referencing this admin to NULL in audit/approval tables
        #    --- REMOVED: UPDATE AdmissionApplications SET approved_by_admin_id = NULL WHERE approved_by_admin_id = %s; ---
        #    Based on error, approved_by_admin_id is not in AdmissionApplications

        # *** VERIFY TABLE AND COLUMN NAMES: admissionstatus.approved_by_admin_id ***
        sql_nullify_admission_status = "UPDATE admissionstatus SET approved_by_admin_id = NULL WHERE approved_by_admin_id = %s;"
        cur.execute(sql_nullify_admission_status, (admin_id,))
        print(f"Set approved_by_admin_id to NULL for {cur.rowcount} admission status entries approved by admin {admin_id}") # Debug print


        # 2. Set the administrator's user_account_id to NULL
        # This must happen before deleting the user account (FK administrators.user_account_id -> useraccounts)
        sql_set_user_account_null = "UPDATE administrators SET user_account_id = NULL WHERE admin_id = %s;"
        cur.execute(sql_set_user_account_null, (admin_id,))
        print(f"Set administrators.user_account_id to NULL for admin {admin_id}") # Debug print


        # 3. Delete the linked User Account (if one exists)
        # This can now be done because the admin record no longer references it (FK useraccounts.entity_id -> administrators)
        if linked_user_account_id:
            sql_delete_user = "DELETE FROM useraccounts WHERE user_account_id = %s;"
            cur.execute(sql_delete_user, (linked_user_account_id,))
            print(f"Deleted user account {linked_user_account_id} linked to admin {admin_id}") # Debug print


        # --- 4. Finally, Delete the Administrator Record ---
        sql_delete_admin = "DELETE FROM administrators WHERE admin_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_admin, (admin_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Administrator found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Administrator {admin_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during admin deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during admin deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/departments', methods=['GET'])
@login_required # Protect this route
def list_all_departments(user):
    """
    Retrieves a list of all departments.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the department list."}), 403


    # --- Fetch All Departments Data ---
    conn = None
    cur = None
    departments_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all department details
        # *** CORRECTED: Removed department_code and creation_date columns ***
        sql = """
            SELECT
                d.department_id, -- Primary key
                d.department_name -- Department name
            FROM departments d -- Use the correct table name
            ORDER BY d.department_name; -- Order alphabetically by name
        """
        # Now only selecting columns we know exist based on your schema

        cur.execute(sql)

        departments_list = cur.fetchall()

        return jsonify(departments_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching department list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching department list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/departments/<department_id>', methods=['GET'])
@login_required # Protect this route
def get_department_details_for_admin(user, department_id):
    """
    Retrieves details of a specific department by department_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view department details."}), 403


    # --- Fetch Specific Department Data ---
    conn = None
    cur = None
    department_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant department details for the given department_id
        # Based on previous findings, only department_id and department_name exist
        # *** VERIFY 'departments' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                d.department_id, -- Primary key
                d.department_name -- Department name
                -- Include other columns if they exist in your departments table
            FROM departments d -- *** Use the correct table name ***
            WHERE d.department_id = %s; -- *** Filter by the department_id from the URL path ***
        """

        # Use the department_id from the URL path parameter
        cur.execute(sql, (department_id,))

        department_details = cur.fetchone()

        if department_details is None:
            # Department with the given ID not found
            return jsonify({"error": "Department not found."}), 404 # 404 Not Found

        return jsonify(department_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific department details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific department details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/departments', methods=['POST'])
@login_required # Protect this route
def create_department_for_admin(user):
    """
    Creates a new department via admin dashboard.
    Requires 'admin' role.
    Accepts new department data in JSON request body, including faculty_id.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create departments."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Add faculty_id to required fields
    required_fields = ['department_name', 'faculty_id'] # *** ADDED faculty_id ***
    # if 'department_code' exists and is required: required_fields.append('department_code')

    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    department_name = data.get('department_name')
    faculty_id = data.get('faculty_id') # *** GET faculty_id from request ***
    # department_code = data.get('department_code')


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate department name (assuming unique within a faculty)
        # Modify duplicate check to include faculty_id
        cur.execute("SELECT department_id FROM departments WHERE department_name = %s AND faculty_id = %s;", (department_name, faculty_id)) # *** Modified duplicate check ***
        if cur.fetchone():
             return jsonify({"error": f"Department name '{department_name}' already exists in faculty {faculty_id}."}), 409 # 409 Conflict

        # If department_code exists and is unique, check for duplicate code (potentially within faculty)
        # if 'department_code' in data and department_code:
        #     cur.execute("SELECT department_id FROM departments WHERE department_code = %s;", (department_code,)) # Or check within faculty?
        #     if cur.fetchone():
        #         return jsonify({"error": f"Department code '{department_code}' already exists."}), 409

        # Check if faculty_id is valid (recommended)
        # cur.execute("SELECT faculty_id FROM faculties WHERE faculty_id = %s;", (faculty_id,)) # Assuming a 'faculties' table
        # if not cur.fetchone():
        #      return jsonify({"error": f"Faculty ID '{faculty_id}' not found."}), 400


        # --- Create Department Record ---
        # Insert into the departments table
        # Include faculty_id in the INSERT statement
        # *** CORRECTED: Added faculty_id to columns and values ***
        sql_insert_department = """
            INSERT INTO departments (department_name, faculty_id) -- *** ADDED faculty_id ***
            VALUES (%s, %s) -- *** ADDED placeholder for faculty_id ***
            RETURNING department_id;
        """
        # Adjust the values tuple to match the columns in INSERT
        execute_values = (department_name, faculty_id) # *** ADDED faculty_id value ***
        # if 'department_code' in data: execute_values = (department_name, faculty_id, department_code) # Adjust order if needed


        cur.execute(sql_insert_department, execute_values)
        new_department_id = cur.fetchone()[0]


        conn.commit()

        # Optional: Fetch and return the full details of the newly created department
        # Using the GET /admin/departments/<department_id> logic is cleaner
        # For simplicity now, return success message and the new ID

        return jsonify({
            "message": f"Department '{department_name}' created successfully!",
            "department_id": new_department_id,
            "department_name": department_name, # Include name for confirmation
            "faculty_id": faculty_id # *** Include faculty_id in response ***
            # Include department_code if it exists and was provided
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during department creation: {e}")
        # This could happen due to duplicate department name/code (now including faculty), or invalid FKs
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during department creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during department creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/departments/<department_id>', methods=['PUT'])
@login_required # Protect this route
def update_department_details_for_admin(user, department_id):
    """
    Updates details of a specific department by department_id for admin view.
    Requires 'admin' role.
    Accepts updated department data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update department details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your schema, department_name and faculty_id seem relevant.
    # If department_code exists and is updatable, add it here.
    updatable_fields = ['department_name', 'faculty_id']
    # if 'department_code' exists and is updatable: updatable_fields.append('department_code')

    update_data = {}
    for field in updatable_fields:
        # Only include fields present in the request body
        if field in data:
            update_data[field] = data[field]

    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor for fetching updated details

        # --- First, verify if the department exists ---
        # *** VERIFY 'departments' TABLE NAME AND 'department_id' COLUMN ***
        cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (department_id,))
        department_exists = cur.fetchone()
        if department_exists is None:
            return jsonify({"error": "Department not found."}), 404


        # --- Basic Validation (More robust validation needed) ---
        # If department_name is being updated, check for duplicate name within the target faculty
        if 'department_name' in update_data:
            target_faculty_id = update_data.get('faculty_id', None) # Check against provided faculty_id if updating faculty, else current faculty
            if target_faculty_id is None:
                # If faculty_id is not in update_data, get the current faculty_id of the department
                cur.execute("SELECT faculty_id FROM departments WHERE department_id = %s;", (department_id,))
                current_faculty_row = cur.fetchone()
                if current_faculty_row:
                     target_faculty_id = current_faculty_row['faculty_id']
                else:
                    # Should not happen if department_exists passed, but as safeguard
                     return jsonify({"error": "Could not determine current faculty for department."}), 500 # Or handle differently

            # Check for duplicate name within the determined faculty, excluding the department being updated
            cur.execute(
                 "SELECT department_id FROM departments WHERE department_name = %s AND faculty_id = %s AND department_id != %s;",
                 (update_data['department_name'], target_faculty_id, department_id)
             )
            if cur.fetchone():
                 return jsonify({"error": f"Department name '{update_data['department_name']}' already exists in faculty {target_faculty_id} (excluding this department)."}), 409


        # If faculty_id is being updated, validate if it's a real faculty ID (recommended)
        # if 'faculty_id' in update_data:
        #     cur.execute("SELECT faculty_id FROM faculties WHERE faculty_id = %s;", (update_data['faculty_id'],))
        #     if not cur.fetchone():
        #         return jsonify({"error": f"Faculty ID '{update_data['faculty_id']}' not found."}), 400

        # If department_code exists and is being updated and is unique, check for duplicate code
        # if 'department_code' in update_data and update_data['department_code']:
        #     cur.execute("SELECT department_id FROM departments WHERE department_code = %s AND department_id != %s;", (update_data['department_code'], department_id))
        #     if cur.fetchone():
        #         return jsonify({"error": f"Department code '{update_data['department_code']}' already exists (excluding this department)."}), 409


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE departments -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE department_id = %s; -- *** Filter by the department_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [department_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Department found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated department details
        # Reuse the GET /admin/departments/<department_id> logic or query again
        # Assuming GET /admin/departments/<department_id> only selects department_id and department_name
        # Fetch specifically if needed, or rely on GET route
        cur.execute(
             """
            SELECT
                d.department_id, d.department_name, d.faculty_id -- Add other columns if needed
                -- Include department_code if it exists
            FROM departments d
            WHERE d.department_id = %s;
            """, (department_id,))
        updated_department_details = cur.fetchone()


        return jsonify(updated_department_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during department update: {e}")
        # This could happen if department_name/code becomes a duplicate, or faculty_id is invalid
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during department update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during department update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/departments/<department_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_department_for_admin(user, department_id):
    """
    Deletes a specific department by department_id for admin view,
    setting FKs in related tables to NULL.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete departments."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the department exists ---
        # *** VERIFY 'departments' TABLE NAME AND 'department_id' COLUMN ***
        cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (department_id,))
        department_exists = cur.fetchone()
        if department_exists is None:
            return jsonify({"error": "Department not found."}), 404


        # --- Update Related Records (Set FKs to NULL) ---

        # 1. Set department_id to NULL for students in this department
        # *** VERIFY 'students' TABLE NAME AND 'department_id' COLUMN ***
        sql_nullify_student_dept = "UPDATE students SET department_id = NULL WHERE department_id = %s;"
        cur.execute(sql_nullify_student_dept, (department_id,))
        print(f"Set department_id to NULL for {cur.rowcount} students in department {department_id}") # Debug print

        # 2. Set department_id to NULL for lecturers in this department
        # *** VERIFY 'lecturers' TABLE NAME AND 'department_id' COLUMN ***
        sql_nullify_lecturer_dept = "UPDATE lecturers SET department_id = NULL WHERE department_id = %s;"
        cur.execute(sql_nullify_lecturer_dept, (department_id,))
        print(f"Set department_id to NULL for {cur.rowcount} lecturers in department {department_id}") # Debug print

        # 3. Set department_id to NULL for courses in this department
        # *** VERIFY 'courses' TABLE NAME AND 'department_id' COLUMN ***
        sql_nullify_course_dept = "UPDATE courses SET department_id = NULL WHERE department_id = %s;"
        cur.execute(sql_nullify_course_dept, (department_id,))
        print(f"Set department_id to NULL for {cur.rowcount} courses in department {department_id}") # Debug print


        # --- Finally, Delete the Department Record ---
        sql_delete_department = "DELETE FROM departments WHERE department_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_department, (department_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Department found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Department {department_id} and linked records updated successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during department deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled or wasn't set to NULL!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during department deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/academic-years', methods=['GET'])
@login_required # Protect this route
def list_all_academic_years(user):
    """
    Retrieves a list of all academic years.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the academic year list."}), 403


    # --- Fetch All Academic Years Data ---
    conn = None
    cur = None
    academic_years_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all academic year details
        # *** VERIFY 'academicyears' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                ay.academic_year_id, -- Primary key
                ay.term_name, -- e.g., '2023/2024' or 'Fall 2023/Spring 2024'
                ay.start_date, -- Assuming start_date exists
                ay.end_date -- Assuming end_date exists
            FROM academicyears ay -- *** Use the correct table name ***
            ORDER BY ay.term_name DESC; -- Order by year name, maybe start_date
        """
        # Note: Adjust column names (term_name, start_date, end_date) if your schema is different.
        # If a column doesn't exist, remove it from the SELECT list.


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        academic_years_list = cur.fetchall()

        # Convert dates to string format for JSON if needed (optional, JSON standard handles datetime)
        # for year in academic_years_list:
        #     if year.get('start_date'):
        #         year['start_date'] = year['start_date'].isoformat() # Or a different format
        #     if year.get('end_date'):
        #         year['end_date'] = year['end_date'].isoformat() # Or a different format


        return jsonify(academic_years_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching academic year list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching academic year list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/academic-years/<year_id>', methods=['GET'])
@login_required # Protect this route
def get_academic_year_details_for_admin(user, year_id):
    """
    Retrieves details of a specific academic year by academic_year_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view academic year details."}), 403


    # --- Fetch Specific Academic Year Data ---
    conn = None
    cur = None
    academic_year_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant academic year details for the given academic_year_id
        # *** VERIFY 'academicyears' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                ay.academic_year_id, -- Primary key
                ay.term_name, -- Name of the term/year
                ay.start_date, -- Assuming start_date exists based on list response
                ay.end_date -- Assuming end_date exists based on list response
                -- Include other columns if they exist in your academicyears table
            FROM academicyears ay -- *** Use the correct table name ***
            WHERE ay.academic_year_id = %s; -- *** Filter by the academic_year_id from the URL path ***
        """

        # Use the academic_year_id from the URL path parameter
        cur.execute(sql, (year_id,))

        academic_year_details = cur.fetchone()

        if academic_year_details is None:
            # Academic year with the given ID not found
            return jsonify({"error": "Academic year not found."}), 404 # 404 Not Found

        # Optional: Convert dates to string format for JSON if needed
        # if academic_year_details:
        #     if academic_year_details.get('start_date'):
        #         academic_year_details['start_date'] = academic_year_details['start_date'].isoformat() # Or different format
        #     if academic_year_details.get('end_date'):
        #         academic_year_details['end_date'] = academic_year_details['end_date'].isoformat() # Or different format


        return jsonify(academic_year_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific academic year details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific academic year details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/academic-years', methods=['POST'])
@login_required # Protect this route
def create_academic_year_for_admin(user):
    """
    Creates a new academic year via admin dashboard.
    Requires 'admin' role.
    Accepts new academic year data in JSON request body, including year.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create academic years."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    required_fields = ['term_name', 'year', 'start_date', 'end_date']

    for field in required_fields:
        if field not in data or data.get(field) is None:
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    term_name = data.get('term_name')
    year_num = data.get('year')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    # Basic validation for year (should be an integer)
    try:
        year_int = int(year_num)
    except (ValueError, TypeError):
        return jsonify({"error": "Field 'year' must be an integer."}), 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- Basic Validation ---
        # Check for duplicate term name
        cur.execute("SELECT academic_year_id FROM academicyears WHERE term_name = %s;", (term_name,))
        if cur.fetchone():
             return jsonify({"error": f"Academic year term name '{term_name}' already exists."}), 409 # 409 Conflict

        # Check for duplicate year number (assuming year number should be unique and stored as VARCHAR)
        # *** CORRECTED: Pass year as string here ***
        cur.execute("SELECT academic_year_id FROM academicyears WHERE year = %s;", (str(year_int),))
        if cur.fetchone():
             return jsonify({"error": f"Academic year year number '{year_int}' already exists."}), 409 # 409 Conflict


        # Validate date formats and logical order (start_date < end_date) - Recommended
        # try:
        #     start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() # Adjust format if needed
        #     end_date_obj = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() # Adjust format if needed
        #     if start_date_obj >= end_date_obj:
        #         return jsonify({"error": "Start date must be before end date."}), 400
        # except ValueError:
        #      return jsonify({"error": "Invalid date format. Use ISO format<ctrl97>YYYY-MM-DD."}), 400


        # --- Create Academic Year Record ---
        # Insert into the academicyears table
        # Include year, start_date, end_date, term_name
        # Assuming column order is academic_year_id, year, start_date, end_date, term_name
        sql_insert_year = """
            INSERT INTO academicyears (year, start_date, end_date, term_name)
            VALUES (%s, %s, %s, %s)
            RETURNING academic_year_id;
        """
        # Pass values in the order matching the columns in INSERT
        # *** CORRECTED: Pass year as string here ***
        execute_values = (str(year_int), start_date_str, end_date_str, term_name)


        cur.execute(sql_insert_year, execute_values)
        new_year_id = cur.fetchone()[0]


        conn.commit()

        return jsonify({
            "message": f"Academic year '{term_name}' ({year_int}) created successfully!",
            "academic_year_id": new_year_id,
            "term_name": term_name,
            "year": year_int, # Return year as integer in response if preferred
            "start_date": start_date_str,
            "end_date": end_date_str
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during academic year creation: {e}")
        # This could happen due to duplicate term_name, year, or invalid/overlapping dates if constraints exist
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during academic year creation: {e}")
        # If date format is wrong and DB rejects it, this will be a Database error
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during academic year creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/academic-years/<year_id>', methods=['PUT'])
@login_required # Protect this route
def update_academic_year_details_for_admin(user, year_id):
    """
    Updates details of a specific academic year by academic_year_id for admin view.
    Requires 'admin' role.
    Accepts updated academic year data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update academic year details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your schema, term_name, year, start_date, and end_date seem relevant.
    updatable_fields = ['term_name', 'year', 'start_date', 'end_date']

    update_data = {}
    for field in updatable_fields:
        # Only include fields present in the request body
        # Check for presence AND not None explicitly if allowing empty strings but not null
        if field in data and data.get(field) is not None:
            update_data[field] = data[field]

    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor for fetching updated details

        # --- First, verify if the academic year exists ---
        # *** VERIFY 'academicyears' TABLE NAME AND 'academic_year_id' COLUMN ***
        cur.execute("SELECT academic_year_id FROM academicyears WHERE academic_year_id = %s;", (year_id,))
        year_exists = cur.fetchone()
        if year_exists is None:
            return jsonify({"error": "Academic year not found."}), 404


        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate term name if it's being updated
        if 'term_name' in update_data:
            cur.execute(
                 "SELECT academic_year_id FROM academicyears WHERE term_name = %s AND academic_year_id != %s;",
                 (update_data['term_name'], year_id)
             )
            if cur.fetchone():
                 return jsonify({"error": f"Academic year term name '{update_data['term_name']}' already exists (excluding this academic year)."}), 409

        # Check for duplicate year number if it's being updated (assuming year is VARCHAR)
        if 'year' in update_data:
            try:
                 year_int = int(update_data['year']) # Validate it's an integer if updating
            except (ValueError, TypeError):
                 return jsonify({"error": "Field 'year' must be an integer."}), 400

            # Check for duplicate year number (stored as VARCHAR)
            cur.execute(
                 "SELECT academic_year_id FROM academicyears WHERE year = %s AND academic_year_id != %s;",
                 (str(year_int), year_id) # *** Pass year as string for comparison ***
             )
            if cur.fetchone():
                 return jsonify({"error": f"Academic year year number '{year_int}' already exists (excluding this academic year)."}), 409
            update_data['year'] = str(year_int) # Store validated string back in update_data


        # Validate date formats and logical order (start_date < end_date) if dates are being updated
        # You'll need to handle cases where only one date is provided or both
        # This can get complex; relying on DB constraints is simpler if they exist.
        # Example if validating both dates together:
        # start_date_update = update_data.get('start_date')
        # end_date_update = update_data.get('end_date')
        # if start_date_update or end_date_update:
        #     # Need to fetch current dates if only one is provided
        #     # Then parse and compare start_date_obj < end_date_obj
        #     pass # Add logic here


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE academicyears -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE academic_year_id = %s; -- *** Filter by the academic_year_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [year_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Academic year found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated academic year details
        # Reuse the GET /admin/academic-years/<year_id> logic or query again
        cur.execute(
             """
            SELECT
                ay.academic_year_id, ay.term_name, ay.year, ay.start_date, ay.end_date
                -- Include other columns if they exist
            FROM academicyears ay
            WHERE ay.academic_year_id = %s;
            """, (year_id,))
        updated_year_details = cur.fetchone()


        return jsonify(updated_year_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during academic year update: {e}")
        # This could happen if term_name/year becomes a duplicate, or date constraints are violated
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during academic year update: {e}")
        # If date format is wrong and DB rejects it, this will be a Database error
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during academic year update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/academic-years/<year_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_academic_year_for_admin(user, year_id):
    """
    Deletes a specific academic year by academic_year_id for admin view,
    setting FKs in related tables to NULL based on schema findings.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete academic years."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the academic year exists ---
        # *** VERIFY 'academicyears' TABLE NAME AND 'academic_year_id' COLUMN ***
        cur.execute("SELECT academic_year_id FROM academicyears WHERE academic_year_id = %s;", (year_id,))
        year_exists = cur.fetchone()
        if year_exists is None:
            return jsonify({"error": "Academic year not found."}), 404


        # --- Update Related Records (Set FKs to NULL) ---

        # 1. Set academic_year_id to NULL for students linked to this year
        #    This query caused a NOT NULL error earlier, which you hopefully fixed by making the column nullable.
        # *** VERIFY 'students' TABLE NAME AND 'academic_year_id' COLUMN ***
        sql_nullify_student_year = "UPDATE students SET academic_year_id = NULL WHERE academic_year_id = %s;"
        cur.execute(sql_nullify_student_year, (year_id,))
        print(f"Set academic_year_id to NULL for {cur.rowcount} students linked to academic year {year_id}") # Debug print

        # 2. Set academic_year_id to NULL for course assignments linked to this year
        #    This query caused an error earlier, which you hopefully fixed by making the column nullable and adding the update.
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'academic_year_id' COLUMN ***
        sql_nullify_assignment_year = "UPDATE coursesassignedtolecturers SET academic_year_id = NULL WHERE academic_year_id = %s;"
        cur.execute(sql_nullify_assignment_year, (year_id,))
        print(f"Set academic_year_id to NULL for {cur.rowcount} course assignments linked to academic year {year_id}") # Debug print

        # 3. Set academic_year_id to NULL for student enrollments linked to this year
        #    *** ADDED: Nullify FK in studentsenrolledcourses ***
        # *** VERIFY 'studentsenrolledcourses' TABLE NAME AND 'academic_year_id' COLUMN ***
        sql_nullify_enrollment_year = "UPDATE studentsenrolledcourses SET academic_year_id = NULL WHERE academic_year_id = %s;"
        cur.execute(sql_nullify_enrollment_year, (year_id,))
        print(f"Set academic_year_id to NULL for {cur.rowcount} student enrollments linked to academic year {year_id}") # Debug print


        # 4. Set academic_year_id to NULL for AdmissionApplications linked to this year
        #    This query caused a "relation does not exist" error earlier, so it might need to be removed if the table doesn't exist or the column name is different.
        # *** VERIFY 'AdmissionApplications' TABLE NAME AND 'academic_year_id' COLUMN (or similar) ***
        # sql_nullify_application_year = "UPDATE \"AdmissionApplications\" SET academic_year_id = NULL WHERE academic_year_id = %s;" # Uncomment and verify if table/column exist
        # cur.execute(sql_nullify_application_year, (year_id,))
        # print(f"Set academic_year_id to NULL for {cur.rowcount} applications linked to academic year {year_id}") # Debug print


        # 5. Set academic_year_id to NULL for admissionstatus linked to this year
        #    This query was commented out previously. If admissionstatus HAS an academic_year_id column
        #    and needs nulling, uncomment and verify table/column name.
        # *** VERIFY 'admissionstatus' TABLE NAME AND 'academic_year_id' COLUMN (or similar) ***
        # sql_nullify_admissionstatus_year = "UPDATE admissionstatus SET academic_year_id = NULL WHERE academic_year_id = %s;"
        # cur.execute(sql_nullify_admissionstatus_year, (year_id,))
        # print(f"Set academic_year_id to NULL for {cur.rowcount} admission status entries linked to academic year {year_id}") # Debug print


        # --- Finally, Delete the Academic Year Record ---
        sql_delete_year = "DELETE FROM academicyears WHERE academic_year_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_year, (year_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Academic year found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Academic year {year_id} and linked records updated successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during academic year deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled or wasn't set to NULL!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during academic year deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/courses', methods=['GET'])
@login_required # Protect this route
def list_all_courses(user):
    """
    Retrieves a list of all courses.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the course list."}), 403


    # --- Fetch All Courses Data ---
    conn = None
    cur = None
    courses_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all course details, join departments for department name
        # Based on previous errors, courses might not be directly linked to academic years
        # by a column named academic_year_id.
        # *** VERIFY 'courses' and 'departments' TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                c.course_id, -- Primary key
                c.course_code, -- e.g., 'CSC 101'
                c.course_title, -- e.g., 'Introduction to Computer Science'
                c.credits, -- e.g., 3
                c.department_id, -- FK to departments
                d.department_name -- Department name from joined table
                -- Include other columns if they exist in your courses table (e.g., academic_year_id if FK column name is different)
            FROM courses c -- *** Use the correct table name ***
            JOIN departments d ON c.department_id = d.department_id -- *** Join departments table ***
            ORDER BY c.course_code; -- Order by course code
        """
        # Note: Adjust column names (course_code, course_title, credits, department_id) if your schema is different.
        # If a column doesn't exist, remove it from the SELECT list.


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        courses_list = cur.fetchall()

        return jsonify(courses_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching course list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching course list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/courses/<course_id>', methods=['GET'])
@login_required # Protect this route
def get_course_details_for_admin(user, course_id):
    """
    Retrieves details of a specific course by course_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view course details."}), 403


    # --- Fetch Specific Course Data ---
    conn = None
    cur = None
    course_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant course details for the given course_id
        # Join departments for department name
        # *** VERIFY 'courses' and 'departments' TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                c.course_id, -- Primary key
                c.course_code,
                c.course_title, -- *** Use the correct column name ***
                c.credits,
                c.department_id, -- FK
                d.department_name -- From joined departments table
                -- Include other columns if they exist in your courses table
            FROM courses c -- *** Use the correct table name ***
            JOIN departments d ON c.department_id = d.department_id -- *** Join departments table ***
            WHERE c.course_id = %s; -- *** Filter by the course_id from the URL path ***
        """

        # Use the course_id from the URL path parameter
        cur.execute(sql, (course_id,))

        course_details = cur.fetchone()

        if course_details is None:
            # Course with the given ID not found
            return jsonify({"error": "Course not found."}), 404 # 404 Not Found

        return jsonify(course_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific course details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific course details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/courses', methods=['POST'])
@login_required # Protect this route
def create_course_for_admin(user):
    """
    Creates a new course via admin dashboard.
    Requires 'admin' role.
    Accepts new course data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create courses."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your schema, course_code, course_title, credits, and department_id are relevant.
    required_fields = ['course_code', 'course_title', 'credits', 'department_id']

    for field in required_fields:
        if field not in data or data.get(field) is None: # Check for None explicitly
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    course_code = data.get('course_code') # Should be unique
    course_title = data.get('course_title')
    credits = data.get('credits') # Should be a number/integer
    department_id = data.get('department_id') # FK to departments


    # --- Basic Validation (More robust validation needed) ---
    # Validate credits is a number
    try:
        credits_num = int(credits) # Or float if credits can be non-integers
        if credits_num <= 0: # Credits should be positive
             return jsonify({"error": "Credits must be a positive number."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Credits must be a number."}), 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # Check for duplicate course code (assuming it should be unique)
        cur.execute("SELECT course_id FROM courses WHERE course_code = %s;", (course_code,))
        if cur.fetchone():
             return jsonify({"error": f"Course code '{course_code}' already exists."}), 409 # 409 Conflict

        # Check if department_id is valid (recommended)
        cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (department_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Department ID '{department_id}' not found."}), 400


        # --- Create Course Record ---
        # Insert into the courses table
        # Assuming course_id is the PK and is generated automatically
        # *** VERIFY column names: course_code, course_title, credits, department_id ***
        sql_insert_course = """
            INSERT INTO courses (course_code, course_title, credits, department_id)
            VALUES (%s, %s, %s, %s)
            RETURNING course_id; -- Assuming PK is returned
        """
        execute_values = (course_code, course_title, credits_num, department_id) # Pass validated credits number

        cur.execute(sql_insert_course, execute_values)
        new_course_id = cur.fetchone()[0]


        conn.commit()

        # Optional: Fetch and return the full details of the newly created course
        # Using the GET /admin/courses/<course_id> logic is cleaner
        # For simplicity now, return success message and the new ID/code/title

        return jsonify({
            "message": f"Course '{course_title}' ({course_code}) created successfully!",
            "course_id": new_course_id,
            "course_code": course_code,
            "course_title": course_title,
            "credits": credits_num,
            "department_id": department_id # Include department_id in response
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during course creation: {e}")
        # This could happen due to duplicate course_code, or invalid department_id if FK constraint fails
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/courses/<course_id>', methods=['PUT'])
@login_required # Protect this route
def update_course_details_for_admin(user, course_id):
    """
    Updates details of a specific course by course_id for admin view.
    Requires 'admin' role.
    Accepts updated course data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update course details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your schema, course_code, course_title, credits, and department_id are relevant.
    updatable_fields = ['course_code', 'course_title', 'credits', 'department_id']

    update_data = {}
    for field in updatable_fields:
        # Only include fields present in the request body and not None
        if field in data and data.get(field) is not None:
             # Validate credits if present
             if field == 'credits':
                 try:
                     credits_num = int(data[field])
                     if credits_num <= 0:
                         return jsonify({"error": "Credits must be a positive number."}), 400
                     update_data[field] = credits_num
                 except (ValueError, TypeError):
                      return jsonify({"error": "Credits must be a number."}), 400
             else:
                update_data[field] = data[field]


    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor for fetching updated details

        # --- First, verify if the course exists ---
        # *** VERIFY 'courses' TABLE NAME AND 'course_id' COLUMN ***
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (course_id,))
        course_exists = cur.fetchone()
        if course_exists is None:
            return jsonify({"error": "Course not found."}), 404


        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate course code if it's being updated
        if 'course_code' in update_data:
            cur.execute(
                 "SELECT course_id FROM courses WHERE course_code = %s AND course_id != %s;",
                 (update_data['course_code'], course_id)
             )
            if cur.fetchone():
                 return jsonify({"error": f"Course code '{update_data['course_code']}' already exists (excluding this course)."}), 409


        # If department_id is being updated, validate if it's a real department ID (recommended)
        if 'department_id' in update_data:
            cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (update_data['department_id'],))
            if not cur.fetchone():
                return jsonify({"error": f"Department ID '{update_data['department_id']}' not found."}), 400


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE courses -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE course_id = %s; -- *** Filter by the course_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [course_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Course found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated course details
        # Use the GET /admin/courses/<course_id> logic or query again
        cur.execute(
             """
            SELECT
                c.course_id, c.course_code, c.course_title, c.credits, c.department_id,
                d.department_name
            FROM courses c
            JOIN departments d ON c.department_id = d.department_id
            WHERE c.course_id = %s;
            """, (course_id,))
        updated_course_details = cur.fetchone()


        return jsonify(updated_course_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during course update: {e}")
        # This could happen if course_code becomes a duplicate, or department_id is invalid
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/courses/<course_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_course_for_admin(user, course_id):
    """
    Deletes a specific course by course_id for admin view,
    including associated records based on ON DELETE NO ACTION schema.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete courses."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the course exists ---
        # *** VERIFY 'courses' TABLE NAME AND 'course_id' COLUMN ***
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (course_id,))
        course_exists = cur.fetchone()
        if course_exists is None:
            return jsonify({"error": "Course not found."}), 404


        # --- Delete Related Records (Order is crucial with NO ACTION!) ---

        # 1. Find all assignment_ids for this course
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'course_id', 'assignment_id' COLUMNS ***
        sql_get_assignments = """
            SELECT assignment_id FROM coursesassignedtolecturers WHERE course_id = %s;
        """
        cur.execute(sql_get_assignments, (course_id,))
        assignment_ids_rows = cur.fetchall()
        # Extract assignment IDs into a list
        assignment_ids = [row[0] for row in assignment_ids_rows]
        print(f"Found {len(assignment_ids)} assignments for course {course_id}: {assignment_ids}") # Debug print


        # 2. If assignments exist, find all session_ids for these assignments
        session_ids = []
        if assignment_ids:
            # Use IN clause to select sessions for any of these assignments
            # *** VERIFY 'attendancesessions' TABLE NAME AND 'assignment_id', 'session_id' COLUMNS ***
            sql_get_sessions = """
                SELECT session_id FROM attendancesessions WHERE assignment_id IN %s;
            """
            # Execute with tuple of assignment_ids for the IN clause
            cur.execute(sql_get_sessions, (tuple(assignment_ids),))
            session_ids_rows = cur.fetchall()
            # Extract session IDs into a list
            session_ids = [row[0] for row in session_ids_rows]
            print(f"Found {len(session_ids)} sessions for assignments: {session_ids}") # Debug print

            # 3. If sessions exist, delete attendance records for these sessions
            # *** VERIFY 'attendancerecords' TABLE NAME AND 'session_id' COLUMN ***
            if session_ids:
                sql_delete_attendance = """
                    DELETE FROM attendancerecords WHERE session_id IN %s;
                """
                 # Execute with tuple of session_ids for the IN clause
                cur.execute(sql_delete_attendance, (tuple(session_ids),))
                print(f"Deleted {cur.rowcount} attendance records for sessions") # Debug print

            # 4. Delete the sessions themselves (if sessions exist)
            # *** VERIFY 'attendancesessions' TABLE NAME ***
            sql_delete_sessions = """
                DELETE FROM attendancesessions WHERE assignment_id IN %s;
            """
            # Execute with tuple of assignment_ids for the IN clause (sessions linked to these assignments)
            cur.execute(sql_delete_sessions, (tuple(assignment_ids),)) # Delete sessions linked to assignments
            print(f"Deleted {cur.rowcount} sessions for assignments") # Debug print


        # 5. Delete student enrollments for this course
        # *** VERIFY 'studentsenrolledcourses' TABLE NAME AND 'course_id' COLUMN ***
        sql_delete_enrollments = "DELETE FROM studentsenrolledcourses WHERE course_id = %s;"
        cur.execute(sql_delete_enrollments, (course_id,))
        print(f"Deleted {cur.rowcount} student enrollments for course {course_id}") # Debug print

        # 6. Delete the course assignments for this course
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME ***
        sql_delete_assignments = "DELETE FROM coursesassignedtolecturers WHERE course_id = %s;"
        cur.execute(sql_delete_assignments, (course_id,))
        print(f"Deleted {cur.rowcount} course assignments for course {course_id}") # Debug print


        # --- Finally, Delete the Course Record ---
        # *** VERIFY 'courses' TABLE NAME ***
        sql_delete_course = "DELETE FROM courses WHERE course_id = %s;"
        cur.execute(sql_delete_course, (course_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Course found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Course {course_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/faculties', methods=['GET'])
@login_required # Protect this route
def list_all_faculties(user):
    """
    Retrieves a list of all faculties.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the faculty list."}), 403


    # --- Fetch All Faculties Data ---
    conn = None
    cur = None
    faculties_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all faculty details
        # *** VERIFY 'faculties' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                f.faculty_id, -- Primary key
                f.faculty_name -- Assuming faculty_name exists
                -- Include other columns if they exist in your faculties table (e.g., dean_id, creation_date)
            FROM faculties f -- *** Use the correct table name (assuming 'faculties') ***
            ORDER BY f.faculty_name; -- Order alphabetically by name
        """
        # Note: Adjust column names (faculty_name) if your schema is different.
        # If a column doesn't exist, remove it from the SELECT list.


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        faculties_list = cur.fetchall()

        return jsonify(faculties_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching faculty list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching faculty list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/faculties/<faculty_id>', methods=['GET'])
@login_required # Protect this route
def get_faculty_details_for_admin(user, faculty_id):
    """
    Retrieves details of a specific faculty by faculty_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view faculty details."}), 403


    # --- Fetch Specific Faculty Data ---
    conn = None
    cur = None
    faculty_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant faculty details for the given faculty_id
        # *** VERIFY 'faculties' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                f.faculty_id, -- Primary key
                f.faculty_name -- Name of the faculty
                -- Include other columns if they exist in your faculties table
            FROM faculties f -- *** Use the correct table name ***
            WHERE f.faculty_id = %s; -- *** Filter by the faculty_id from the URL path ***
        """
        # Note: Adjust column names (faculty_name) if your schema is different.


        # Use the faculty_id from the URL path parameter
        cur.execute(sql, (faculty_id,))

        faculty_details = cur.fetchone()

        if faculty_details is None:
            # Faculty with the given ID not found
            return jsonify({"error": "Faculty not found."}), 404 # 404 Not Found

        return jsonify(faculty_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific faculty details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific faculty details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/faculties', methods=['POST'])
@login_required # Protect this route
def create_faculty_for_admin(user):
    """
    Creates a new faculty via admin dashboard.
    Requires 'admin' role.
    Accepts new faculty data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create faculties."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your schema, faculty_name seems required.
    required_fields = ['faculty_name']

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    faculty_name = data.get('faculty_name')


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate faculty name (assuming it should be unique)
        cur.execute("SELECT faculty_id FROM faculties WHERE faculty_name = %s;", (faculty_name,))
        if cur.fetchone():
             return jsonify({"error": f"Faculty name '{faculty_name}' already exists."}), 409 # 409 Conflict


        # --- Create Faculty Record ---
        # Insert into the faculties table
        # Assuming faculty_id is the PK and is generated automatically
        # *** VERIFY column names: faculty_name ***
        sql_insert_faculty = """
            INSERT INTO faculties (faculty_name) -- *** Adjust column names based on your schema ***
            VALUES (%s)
            RETURNING faculty_id; -- Assuming PK is returned
        """
        execute_values = (faculty_name,)

        cur.execute(sql_insert_faculty, execute_values)
        new_faculty_id = cur.fetchone()[0]


        conn.commit()

        # Optional: Fetch and return the full details of the newly created faculty
        # Using the GET /admin/faculties/<faculty_id> logic is cleaner
        # For simplicity now, return success message and the new ID/name

        return jsonify({
            "message": f"Faculty '{faculty_name}' created successfully!",
            "faculty_id": new_faculty_id,
            "faculty_name": faculty_name # Include name for confirmation
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during faculty creation: {e}")
        # This could happen due to duplicate faculty_name
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during faculty creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during faculty creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/faculties/<faculty_id>', methods=['PUT'])
@login_required # Protect this route
def update_faculty_details_for_admin(user, faculty_id):
    """
    Updates details of a specific faculty by faculty_id for admin view.
    Requires 'admin' role.
    Accepts updated faculty data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update faculty details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your schema, faculty_name is likely the main updatable field.
    updatable_fields = ['faculty_name']
    # Add other updatable fields if they exist (e.g., dean_id)

    update_data = {}
    for field in updatable_fields:
        # Only include fields present in the request body and not None/empty string
        if field in data and data.get(field): # Check for non-empty string
            update_data[field] = data[field]


    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor for fetching updated details

        # --- First, verify if the faculty exists ---
        # *** VERIFY 'faculties' TABLE NAME AND 'faculty_id' COLUMN ***
        cur.execute("SELECT faculty_id FROM faculties WHERE faculty_id = %s;", (faculty_id,))
        faculty_exists = cur.fetchone()
        if faculty_exists is None:
            return jsonify({"error": "Faculty not found."}), 404


        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate faculty name if it's being updated
        if 'faculty_name' in update_data:
            cur.execute(
                 "SELECT faculty_id FROM faculties WHERE faculty_name = %s AND faculty_id != %s;",
                 (update_data['faculty_name'], faculty_id)
             )
            if cur.fetchone():
                 return jsonify({"error": f"Faculty name '{update_data['faculty_name']}' already exists (excluding this faculty)."}), 409


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200

        sql_update = f"""
            UPDATE faculties -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE faculty_id = %s; -- *** Filter by the faculty_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [faculty_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Faculty found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()
        # Return the updated faculty details
        # Use the GET /admin/faculties/<faculty_id> logic or query again
        cur.execute(
             """
            SELECT
                f.faculty_id, f.faculty_name -- Add other columns if needed
            FROM faculties f
            WHERE f.faculty_id = %s;
            """, (faculty_id,))
        updated_faculty_details = cur.fetchone()


        return jsonify(updated_faculty_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during faculty update: {e}")
        # This could happen if faculty_name becomes a duplicate
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during faculty update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during faculty update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/faculties/<faculty_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_faculty_for_admin(user, faculty_id):
    """
    Deletes a specific faculty by faculty_id for admin view,
    setting FKs in related tables (departments) to NULL.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete faculties."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the faculty exists ---
        # *** VERIFY 'faculties' TABLE NAME AND 'faculty_id' COLUMN ***
        cur.execute("SELECT faculty_id FROM faculties WHERE faculty_id = %s;", (faculty_id,))
        faculty_exists = cur.fetchone()
        if faculty_exists is None:
            return jsonify({"error": "Faculty not found."}), 404


        # --- Update Related Records (Set FKs to NULL) ---

        # 1. Set faculty_id to NULL for departments linked to this faculty
        #    We know from previous errors that departments.faculty_id exists and is nullable.
        # *** VERIFY 'departments' TABLE NAME AND 'faculty_id' COLUMN ***
        sql_nullify_department_faculty = "UPDATE departments SET faculty_id = NULL WHERE faculty_id = %s;"
        cur.execute(sql_nullify_department_faculty, (faculty_id,))
        print(f"Set faculty_id to NULL for {cur.rowcount} departments in faculty {faculty_id}") # Debug print

        # Add updates for any other tables that directly reference faculties if they exist
        # e.g., programs.faculty_id -> faculties.faculty_id


        # --- Finally, Delete the Faculty Record ---
        sql_delete_faculty = "DELETE FROM faculties WHERE faculty_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_faculty, (faculty_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Faculty found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Faculty {faculty_id} and linked departments updated successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during faculty deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled or wasn't set to NULL!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during faculty deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/admission-statuses', methods=['GET'])
@login_required # Protect this route
def list_all_admission_statuses(user):
    """
    Retrieves a list of all admission statuses.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the admission status list."}), 403


    # --- Fetch All Admission Statuses Data ---
    conn = None
    cur = None
    statuses_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all admission status details
        # *** VERIFY 'admissionstatus' TABLE NAME AND COLUMN NAMES ***
        # Note: The table name is likely plural 'admissionstatuses' or singular 'admissionstatus'.
        # Based on a previous error message, 'admissionstatus' seemed to be used.
        # Column names might include admission_status_id, status, description, creation_date, etc.
        # We know 'approved_by_admin_id' exists from previous work, but it's not part of the *status definition* itself.
        # Let's assume admission_status_id and status are key.
        sql = """
            SELECT
                s.admission_status_id, -- Primary key
                s.status -- Assuming status exists (e.g., 'Pending', 'Approved', 'Rejected')
                -- Include other relevant columns if they exist (e.g., description)
            FROM admissionstatus s -- *** Use the correct table name (assuming 'admissionstatus') ***
            ORDER BY s.status; -- Order alphabetically by name
        """
        # Note: Adjust column names (admission_status_id, status) if your schema is different.
        # If a column doesn't exist, remove it from the SELECT list.


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        statuses_list = cur.fetchall()

        return jsonify(statuses_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching admission status list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching admission status list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admission-statuses/<status_id>', methods=['GET'])
@login_required # Protect this route
def get_admission_status_details_for_admin(user, status_id):
    """
    Retrieves details of a specific admission status by admission_status_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view admission status details."}), 403


    # --- Fetch Specific Admission Status Data ---
    conn = None
    cur = None
    status_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant admission status details for the given admission_status_id
        # *** VERIFY 'admissionstatus' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                s.admission_status_id, -- Primary key
                s.status -- *** Use the correct column name for the status value ***
                -- Include other columns if they exist in your admissionstatus table (e.g., description)
            FROM admissionstatus s -- *** Use the correct table name ***
            WHERE s.admission_status_id = %s; -- *** Filter by the admission_status_id from the URL path ***
        """
        # Note: Adjust column names if your schema is different.


        # Use the status_id from the URL path parameter
        cur.execute(sql, (status_id,))

        status_details = cur.fetchone()

        if status_details is None:
            # Admission status with the given ID not found
            return jsonify({"error": "Admission status not found."}), 404 # 404 Not Found

        return jsonify(status_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific admission status details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific admission status details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admission-statuses', methods=['POST'])
@login_required # Protect this route
def create_admission_status_for_admin(user):
    """
    Creates a new admission status via admin dashboard.
    Requires 'admin' role.
    Accepts new status data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create admission statuses."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your schema, 'status' seems required.
    required_fields = ['status']
    # If you have a 'description' column and it's required, add it here.

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    status_name = data.get('status')
    # description = data.get('description') # Get if it exists


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation (More robust validation needed) ---
        # Check for duplicate status name (assuming it should be unique)
        cur.execute("SELECT admission_status_id FROM admissionstatus WHERE status = %s;", (status_name,)) # *** Use the correct column name 'status' ***
        if cur.fetchone():
             return jsonify({"error": f"Admission status '{status_name}' already exists."}), 409 # 409 Conflict


        # --- Create Admission Status Record ---
        # Insert into the admissionstatus table
        # Assuming admission_status_id is the PK and is generated automatically
        # *** VERIFY column names: status ***
        sql_insert_status = """
            INSERT INTO admissionstatus (status) -- *** Use the correct column name ***
            VALUES (%s)
            RETURNING admission_status_id; -- Assuming PK is returned
        """
        # Adjust the values tuple to match the columns in INSERT
        execute_values = (status_name,)
        # if 'description' exists: sql_insert_status = "INSERT INTO admissionstatus (status, description) VALUES (%s, %s) RETURNING admission_status_id;" ; execute_values = (status_name, description)


        cur.execute(sql_insert_status, execute_values)
        new_status_id = cur.fetchone()[0]


        conn.commit()

        # For simplicity, return success message and the new ID/name
        return jsonify({
            "message": f"Admission status '{status_name}' created successfully!",
            "admission_status_id": new_status_id,
            "status": status_name # Include status name for confirmation
            # Include description if it exists and was provided
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during admission status creation: {e}")
        # This could happen due to duplicate status name
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during admission status creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during admission status creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/admission-statuses/<status_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_admission_status_for_admin(user, status_id):
    """
    Deletes a specific admission status by admission_status_id for admin view.
    Removes FK nulling based on schema findings.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete admission statuses."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the admission status exists ---
        # *** VERIFY 'admissionstatus' TABLE NAME AND 'admission_status_id' COLUMN ***
        cur.execute("SELECT admission_status_id FROM admissionstatus WHERE admission_status_id = %s;", (status_id,))
        status_exists = cur.fetchone()
        if status_exists is None:
            return jsonify({"error": "Admission status not found."}), 404


        # --- Delete Related Records (Handle FKs pointing TO admissionstatus) ---

        # Based on the provided schema for admissionapplications, it does NOT have a foreign key
        # referencing admissionstatus. So, no UPDATE is needed on admissionapplications here.
        #
        # If there are *any other tables* in your database that *do* have a foreign key
        # referencing admissionstatus.admission_status_id, you would need to add an UPDATE
        # statement here to set that foreign key to NULL (if the column is nullable)
        # or delete the referencing records.
        # Example: If a table called 'status_history' had a column 'previous_status_id'
        # pointing to admissionstatus.admission_status_id:
        # sql_nullify_status_history_fk = "UPDATE status_history SET previous_status_id = NULL WHERE previous_status_id = %s;"
        # cur.execute(sql_nullify_status_history_fk, (status_id,))
        # print(f"Set previous_status_id to NULL for {cur.rowcount} status history entries linked to status {status_id}")


        # --- Finally, Delete the Admission Status Record ---
        sql_delete_status = "DELETE FROM admissionstatus WHERE admission_status_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_status, (status_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             return jsonify({"error": "Admission status found but could not be deleted."}), 500

        conn.commit()
        # Message adjusted as we are not necessarily updating other tables
        return jsonify({"message": f"Admission status {status_id} deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during admission status deletion: {e}")
        # If you get a foreign key violation here, it means some *other* table references
        # admissionstatus.admission_status_id and wasn't handled!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during admission status deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/applications', methods=['GET'])
@login_required # Protect this route
def list_all_applications(user):
    """
    Retrieves a list of all admission applications.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the application list."}), 403


    # --- Fetch All Applications Data ---
    conn = None
    cur = None
    applications_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all application details based on your schema output
        # *** VERIFY 'admissionapplications' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                a.application_id,
                a.first_name,
                a.last_name,
                a.email,
                a.contact_number,
                a.date_of_birth,
                a.gender,
                a.level,
                a.intended_department_name,
                a.intended_program,
                a.proposed_username, -- Might be sensitive, decide if you want to list this
                a.application_date,
                a.application_status -- Note: This is a VARCHAR based on your schema
                -- Include other columns if they exist and are needed for the list view
            FROM admissionapplications a -- *** Use the correct table name (lowercase) ***
            ORDER BY a.application_date DESC; -- Order by application date
        """
        # Note: Adjust column names if your schema output had different names or types.
        # If a column doesn't exist, remove it from the SELECT list.
        # Consider if you want to expose 'proposed_username' in a list view.


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        applications_list = cur.fetchall()

        # Optional: Convert dates/timestamps to string format for JSON if needed
        # for app in applications_list:
        #     if app.get('date_of_birth'):
        #         app['date_of_birth'] = app['date_of_birth'].isoformat()
        #     if app.get('application_date'):
        #         app['application_date'] = app['application_date'].isoformat()


        return jsonify(applications_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching application list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching application list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/applications/<application_id>', methods=['GET'])
@login_required # Protect this route
def get_application_details_for_admin(user, application_id):
    """
    Retrieves details of a specific admission application by application_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view application details."}), 403


    # --- Fetch Specific Application Data ---
    conn = None
    cur = None
    application_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant application details for the given application_id based on your schema
        # *** VERIFY 'admissionapplications' TABLE NAME AND COLUMN NAMES ***
        sql = """
            SELECT
                a.application_id, -- Primary key
                a.first_name,
                a.last_name,
                a.email,
                a.contact_number,
                a.date_of_birth,
                a.gender,
                a.level,
                a.intended_department_name,
                a.intended_program,
                a.proposed_username,
                a.proposed_password, -- *** CAUTION: Consider if you want to return plain text passwords ***
                a.application_date,
                a.application_status -- Note: This is a VARCHAR
                -- Include other columns if they exist in your admissionapplications table
            FROM admissionapplications a -- *** Use the correct table name ***
            WHERE a.application_id = %s; -- *** Filter by the application_id from the URL path ***
        """

        # Use the application_id from the URL path parameter
        cur.execute(sql, (application_id,))

        application_details = cur.fetchone()

        if application_details is None:
            # Application with the given ID not found
            return jsonify({"error": "Application not found."}), 404 # 404 Not Found

        # Optional: Convert dates/timestamps to string format for JSON if needed
        # if application_details:
        #     if application_details.get('date_of_birth'):
        #         application_details['date_of_birth'] = application_details['date_of_birth'].isoformat()
        #     if application_details.get('application_date'):
        #         application_details['application_date'] = application_details['application_date'].isoformat()

        # *** CAUTION: Consider removing 'proposed_password' from the response before jsonify ***
        # if application_details and 'proposed_password' in application_details:
        #      del application_details['proposed_password']


        return jsonify(application_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific application details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific application details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/applications', methods=['POST'])
@login_required # Protect this route
def create_application_for_admin(user):
    """
    Creates a new admission application via admin dashboard.
    Requires 'admin' role.
    Accepts new application data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create applications."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your schema output (NOT NULL columns)
    required_fields = [
        'first_name',
        'last_name',
        'email',
        'level',
        'intended_department_name',
        'intended_program'
    ]
    # Note: application_id is generated by trigger.
    # contact_number, date_of_birth, gender, proposed_username, proposed_password, application_date, application_status are nullable/have defaults.

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data - include nullable/optional fields if present
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    contact_number = data.get('contact_number')
    date_of_birth_str = data.get('date_of_birth') # Will need parsing if not None
    gender = data.get('gender')
    level = data.get('level')
    intended_department_name = data.get('intended_department_name')
    intended_program = data.get('intended_program')
    proposed_username = data.get('proposed_username')
    proposed_password = data.get('proposed_password')
    application_status = data.get('application_status', 'Pending') # Use default 'Pending' if not provided
    # application_date will use the default CURRENT_TIMESTAMP

    # --- Basic Validation ---
    # Validate email format (basic check)
    # if email and '@' not in email:
    #      return jsonify({"error": "Invalid email format."}), 400

    # Validate date_of_birth format and parse if provided
    date_of_birth_obj = None
    if date_of_birth_str:
        try:
            # Adjust date format string '%Y-%m-%d' if your frontend sends it differently
            # *** CORRECTED LINE: Use datetime.strptime ***
            date_of_birth_obj = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date of birth format. Use YYYY-MM-DD."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # Check for duplicate email (Unique constraint in schema)
        cur.execute("SELECT application_id FROM admissionapplications WHERE email = %s;", (email,))
        if cur.fetchone():
             return jsonify({"error": f"Application with email '{email}' already exists."}), 409 # 409 Conflict

        # Check for duplicate proposed_username if provided (Unique constraint in schema)
        if proposed_username: # Only check if username is provided in request
            cur.execute("SELECT application_id FROM admissionapplications WHERE proposed_username = %s;", (proposed_username,))
            if cur.fetchone():
                 return jsonify({"error": f"Proposed username '{proposed_username}' already exists."}), 409 # 409 Conflict


        # --- Create Application Record ---
        # Insert into the admissionapplications table
        # Exclude application_id (generated by trigger)
        # Exclude application_date (has default) if not providing a value
        # Include all other columns based on schema output
        # *** VERIFY column names and order match your schema ***
        sql_insert_app = """
            INSERT INTO admissionapplications (
                first_name, last_name, email, contact_number, date_of_birth, gender,
                level, intended_department_name, intended_program, proposed_username,
                proposed_password, application_status -- application_date uses default
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING application_id; -- Get the generated ID
        """
        # Pass values matching the column order in INSERT
        execute_values = (
            first_name,
            last_name,
            email,
            contact_number, # Can be NULL if not provided
            date_of_birth_obj, # Pass parsed date object or None
            gender,           # Can be NULL
            level,
            intended_department_name,
            intended_program,
            proposed_username, # Can be NULL
            proposed_password, # Can be NULL (though sensitive!)
            application_status # Uses 'Pending' default if not in data, or the provided value
        )

        cur.execute(sql_insert_app, execute_values)
        new_application_id = cur.fetchone()[0]


        conn.commit()

        # Return success message and the new ID
        # You might want to fetch the full record using GET route here for consistency
        return jsonify({
            "message": f"Application {new_application_id} created successfully!",
            "application_id": new_application_id
            # Optionally return more created data if needed
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during application creation: {e}")
        # This could happen due to duplicate email or username, or other constraints
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during application creation: {e}")
        # This could happen if a date format is wrong (if not validated client/server side)
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during application creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/admin/admission-applications/<application_id>', methods=['PUT'])
@login_required # Protect this route
def update_admission_application_details_for_admin(user, application_id):
    """
    Updates the status and handles approval/rejection of a specific admission application.
    Requires 'admin' role.
    Accepts update data (primarily 'status', and 'matriculation_number' for approval)
    in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update admission applications."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # Define fields that are allowed for generic update if needed (e.g., review notes)
    # updatable_application_fields = ['reviewer_notes', 'recommended_program']


    # --- Check if 'status' update is requested ---
    # The key in the incoming JSON body is still expected to be 'status' for convenience
    new_status = data.get('status')
    matriculation_number = data.get('matriculation_number') # Expected for approval


    # --- Use psycopg2 context managers for connection and transaction ---
    try:
        # 'with' statement manages the connection and transaction automatically
        with psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS) as conn:
            # Cursors created within the 'with conn:' block are part of the transaction
            with conn.cursor() as cur: # Standard cursor (for INSERT, UPDATE, DELETE, simple fetches by index)
                 with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur_dict: # Dict cursor (for SELECT where column names are needed)

                    # --- Step 1: Verify Application Exists and Get Current Details ---
                    # Use dict cursor as we'll access details by column name
                    cur_dict.execute("""
                        SELECT
                            *, -- Select all columns from admissionapplications
                            application_status,
                            intended_department_name,
                            proposed_username,
                            proposed_password,
                            first_name, -- Needed for QR data
                            last_name,  -- Needed for QR data
                            level, -- *** CORRECT THIS COLUMN NAME *** Needed for QR data and mapping to students
                            intended_program -- Needed for mapping to students intended_program
                            -- Ensure all columns mapped to students table are selected here
                            -- (e.g., email, contact_number, date_of_birth, gender)
                        FROM admissionapplications
                        WHERE application_id = %s;
                    """, (application_id,))
                    application_details = cur_dict.fetchone() # Fetch using dict cursor
                    if application_details is None:
                        # The 'with conn:' block will handle connection closing
                        return jsonify({"error": "Admission application not found."}), 404

                    # Access correct status column name from the fetched dictionary
                    current_status = application_details['application_status']


                    # --- Step 2: Handle Status Update and Approval Workflow ---

                    # Define allowed statuses for updating
                    allowed_update_statuses = ['Approved', 'Rejected', 'Pending', 'Under Review'] # Adjust based on your AdmissionStatuses table

                    if new_status is not None: # Only proceed if status is provided for update

                        if not isinstance(new_status, str) or new_status.strip() not in allowed_update_statuses:
                             # The 'with conn:' block will handle rollback on error
                             return jsonify({"error": f"Invalid or unsupported status: '{new_status}'. Allowed: {', '.join(allowed_update_statuses)}."}), 400

                        # --- Case: Approving the Application ---
                        if new_status.strip() == 'Approved':

                            if current_status == 'Approved':
                                # The 'with conn:' block will handle connection closing
                                return jsonify({"message": f"Application '{application_id}' is already Approved."}), 200 # Or 409 Conflict

                            # Require matriculation number for approval
                            if not matriculation_number or not isinstance(matriculation_number, str) or not matriculation_number.strip():
                                 # The 'with conn:' block will handle rollback on error
                                 return jsonify({"error": "Matriculation number is required in the request body for approval."}), 400

                            # Validate matriculation number format (Optional)


                            # Check if matriculation number is already used by another student
                            # Use standard cursor for this simple fetch by index
                            cur.execute("SELECT student_id FROM students WHERE matriculation_number = %s;", (matriculation_number.strip(),))
                            if cur.fetchone():
                                # Raise an exception to trigger rollback via 'with conn:' block's error handling
                                raise psycopg2.IntegrityError(f"Matriculation number '{matriculation_number.strip()}' is already assigned to another student.")


                            # Update application status to Approved
                            # Use standard cursor for UPDATE
                            sql_update_app_status = "UPDATE admissionapplications SET application_status = %s WHERE application_id = %s;" # Use the correct column name you confirmed
                            cur.execute(sql_update_app_status, ('Approved', application_id))


                            # Create a new Student record from application data
                            # Need to map application_details fields to students table columns
                            # Find department_id from intended_department_name
                            # Access correct column name from the fetched dictionary using dict cursor
                            intended_dept_name = application_details.get('intended_department_name', '')
                            # Use standard cursor for simple fetch by index
                            cur.execute("SELECT department_id FROM departments WHERE department_name = %s;", (intended_dept_name,))
                            dept_row = cur.fetchone()
                            if dept_row is None:
                                 # Raise an exception to trigger rollback
                                 raise Exception(f"Department name '{intended_dept_name if intended_dept_name else 'N/A'}' from application not found in departments table. Cannot create student.")
                            student_department_id = dept_row[0] # Access by index


                            # --- Create the User Account using applicant's proposed credentials ---
                            # Fetch proposed username and password from application details (already in application_details from dict cursor)
                            proposed_username = application_details.get('proposed_username')
                            proposed_password_plain = application_details.get('proposed_password') # This is the plain text password from the applicant

                            # Basic validation for proposed credentials from the application
                            if not proposed_username or not isinstance(proposed_username, str) or not proposed_username.strip():
                                # Raise exception to trigger rollback
                                raise Exception("Cannot approve: Admission application is missing a valid proposed username.")
                            if not proposed_password_plain or not isinstance(proposed_password_plain, str):
                                # Raise exception to trigger rollback
                                raise Exception("Cannot approve: Admission application is missing a proposed password.")


                            # Hash the applicant's proposed password (NEVER store plain text password)
                            hashed_proposed_password = generate_password_hash(proposed_password_plain)

                            # Check if the proposed username is already used by another user account
                            # Use standard cursor for this simple fetch by index
                            cur.execute("SELECT user_account_id FROM useraccounts WHERE username = %s;", (proposed_username.strip(),))
                            if cur.fetchone():
                                 # Raise an exception to trigger rollback
                                 raise Exception(f"Cannot approve: Proposed username '{proposed_username.strip()}' is already in use.") # Or return 409 directly if preferred


                            # Create the User Account with proposed username and hashed password
                            # Use standard cursor for INSERT and fetching returned ID by index
                            sql_create_user = """
                                 INSERT INTO useraccounts (username, password, role) -- Use your correct hashed password column name: 'password'
                                 VALUES (%s, %s, 'student')
                                 RETURNING user_account_id; -- Get the generated user_account_id
                            """
                            # Use the proposed username and the hashed proposed password
                            cur.execute(sql_create_user, (proposed_username.strip(), hashed_proposed_password))
                            new_user_account_id = cur.fetchone()[0] # Fetch by index

                            # --- End Create User Account ---


                            # Create the Student record
                            # Use standard cursor for INSERT and fetching returned ID by index
                            sql_create_student = """
                                INSERT INTO students (
                                    user_account_id,
                                    first_name,
                                    last_name,
                                    matriculation_number,
                                    level,              -- Map from application
                                    intended_program,   -- Map from application
                                    department_id,      -- Mapped from application intended_department_name
                                    email,              -- From application?
                                    contact_number,     -- From application?
                                    date_of_birth,      -- From application?
                                    gender,             -- From application?
                                    admission_date      -- Set to approval date (now)
                                    -- Add other student columns based on your students schema
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING student_id; -- Get the generated student_id
                            """
                            # Example mapping (ADJUST BASED ON YOUR admissionapplications AND students SCHEMAS)
                            # Ensure application_details keys match your admissionapplications column names
                            # Use the correct column name for the applicant's chosen level here
                            applicant_level = application_details.get('YOUR_LEVEL_COLUMN_NAME', '100') # *** CORRECT THIS COLUMN NAME ***
                            cur.execute(sql_create_student, (
                                new_user_account_id,
                                application_details.get('first_name', ''),
                                application_details.get('last_name', ''),
                                matriculation_number.strip(), # Use the matriculation number from the request body
                                applicant_level, # Use the applicant's level from the application
                                application_details.get('program_choice', ''), # Map from application
                                student_department_id, # The department ID we found
                                application_details.get('email', ''),
                                application_details.get('contact_number', ''),
                                application_details.get('date_of_birth'),
                                application_details.get('gender', 'Unknown'),
                                datetime.now(timezone.utc) # Admission date is now (approval date)
                                # Map other fields here
                            ))
                            new_student_id = cur.fetchone()[0] # Fetch by index


                            # Update the useraccount to link to the new student record (set entity_id)
                            # Use standard cursor for UPDATE
                            sql_update_user_entity = "UPDATE useraccounts SET entity_id = %s WHERE user_account_id = %s;"
                            cur.execute(sql_update_user_entity, (new_student_id, new_user_account_id))

                            # --- Generate and Store QR Code Data ---
                            # Fetch details from the newly created student record for consistency
                            # *** Use Dict cursor for fetching student details so you can access by name ***
                            cur_dict.execute("""
                                SELECT first_name, last_name, matriculation_number, level, department_id
                                FROM students
                                WHERE student_id = %s;
                            """, (new_student_id,))
                            new_student_details = cur_dict.fetchone() # <-- Fetch using dict cursor!

                            if new_student_details is None:
                                 # This should ideally not happen if student creation was successful
                                 raise Exception(f"Failed to fetch details for newly created student {new_student_id} for QR code generation.")

                            # Fetch department name using the department_id from the new student record
                            # *** Use Dict cursor for fetching department name ***
                            cur_dict.execute("SELECT department_name FROM departments WHERE department_id = %s;", (new_student_details['department_id'],)) # Accessing dict result by name is fine
                            dept_name_row = cur_dict.fetchone() # <-- Fetch using dict cursor!
                            department_name = dept_name_row['department_name'] if dept_name_row else 'Unknown Department' # Accessing dict result by name is fine


                            # Format the QR code data string
                            qr_data_string = (
                                f"ID:{new_student_id},"
                                f"Name:{new_student_details['first_name']} {new_student_details['last_name']}," # Access dict result by name - OK now
                                f"Matric:{new_student_details['matriculation_number']}," # Access dict result by name - OK now
                                f"Level:{new_student_details['level']}," # Access dict result by name - OK now
                                f"Dept:{department_name}"
                            )

                            # Update the new student record with the QR code data
                            # Use standard cursor for UPDATE
                            sql_update_student_qr = "UPDATE students SET qr_code_data = %s WHERE student_id = %s;"
                            cur.execute(sql_update_student_qr, (qr_data_string, new_student_id))
                            # --- End Generate and Store QR Code Data ---


                            # If the 'with conn:' block exits here without error, the transaction is COMMITTED automatically.
                            return jsonify({
                                "message": f"Application '{application_id}' approved! Student, user account, and QR code data created.",
                                "student_id": new_student_id,
                                "user_account_id": new_user_account_id,
                                "username": proposed_username.strip(), # Return the username used (proposed)
                                # Do NOT return the password here
                                "generated_qr_data": qr_data_string # Optionally return the generated QR data string
                            }), 200 # 200 OK


                        # --- Case: Rejecting the Application ---
                        elif new_status.strip() == 'Rejected':
                             if current_status == 'Rejected':
                                # The 'with conn:' block will handle connection closing
                                return jsonify({"message": f"Application '{application_id}' is already Rejected."}), 200 # Or 409 Conflict


                             # Update application status to Rejected
                             # Use standard cursor for UPDATE
                             sql_update_app_status = "UPDATE admissionapplications SET application_status = %s WHERE application_id = %s;" # Use the correct column name you confirmed
                             cur.execute(sql_update_app_status, ('Rejected', application_id))

                             # No student/user account creation on rejection or QR code generation

                             # If the 'with conn:' block exits here without error, the transaction is COMMITTED automatically.
                             return jsonify({"message": f"Application '{application_id}' rejected!"}), 200 # 200 OK


                        # --- Case: Other Status Updates (e.g., 'Under Review', 'Pending') ---
                        else:
                             # Just update the status generically if it's not Approved/Rejected
                             if current_status == new_status.strip():
                                  # The 'with conn:' block will handle connection closing
                                  return jsonify({"message": f"Application '{application_id}' status is already '{current_status}'."}), 200

                             # Use standard cursor for UPDATE
                             sql_update_app_status = "UPDATE admissionapplications SET application_status = %s WHERE application_id = %s;" # Use the correct column name you confirmed
                             cur.execute(sql_update_app_status, (new_status.strip(), application_id))

                             # If the 'with conn:' block exits here without error, the transaction is COMMITTED automatically.
                             return jsonify({"message": f"Application '{application_id}' status updated to '{new_status.strip()}'."}), 200


                    else: # 'status' was not provided in the request body

                        # --- Handle Generic Updates (if any allowed_application_fields were defined) ---
                        # If you had other fields Admins could update in the application (e.g., reviewer_notes)
                        # You would build a dynamic UPDATE query here similar to other PUT routes
                        # For now, since we're focused on status/approval, if status is not provided
                        # and no other updatable fields are handled, return a message or error.
                        # If you defined updatable_application_fields and processed them in update_data:
                        # if update_data:
                        #    # Build and execute dynamic update query for admissionapplications
                        #    pass # ... implement dynamic update ...
                        # else:
                        # The 'with conn:' block will handle connection closing
                        return jsonify({"message": "No 'status' field provided for update. No action taken."}), 200 # Or 400 if status is expected


    except psycopg2.IntegrityError as e:
         # Catch specific integrity errors (like duplicate matriculation number/username)
         # The 'with conn:' block will automatically ROLLBACK the transaction.
         print(f"Integrity error during approval transaction for application {application_id}: {e}")
         error_message = str(e)
         if 'violates unique constraint "students_matriculation_number_key"' in error_message: # Adjust constraint name if different
              return jsonify({"error": f"Database error: Matriculation number '{matriculation_number.strip()}' is already in use."}), 409
         # IMPORTANT: Check for unique constraint violation on username now (using 'username' column)
         elif 'violates unique constraint "useraccounts_username_key"' in error_message: # Adjust constraint name if different
             # The error message might include the username value, which is helpful
             # Check if proposed_username was used, otherwise use the original error message
             username_in_error = proposed_username.strip() if 'proposed_username' in locals() and proposed_username else 'provided username'
             return jsonify({"error": f"Database error: Username '{username_in_error}' is already in use."}), 409 # Return proposed username in message
         # Catch FK violation on department_id if it wasn't caught by explicit check (less likely now)
         # elif 'violates foreign key constraint' in error_message and '"students_department_id_fkey"' in error_message: # Adjust constraint name
         #     return jsonify({"error": "Database error: Invalid department specified for student."}), 409
         return jsonify({"error": f"Database integrity error during approval: {e}"}), 409 # 409 Conflict


    except Exception as e:
        # Catch other exceptions during the process (e.g., department lookup failed, missing proposed credentials)
        # The 'with conn:' block will automatically ROLLBACK the transaction.
        print(f"An error occurred during admission application update/approval for application {application_id}: {e}")
        # Check if the error was one of the specific exceptions we raised
        error_message_str = str(e)
        if isinstance(e, Exception) and ("from application not found in departments table" in error_message_str or "Admission application is missing a valid proposed username" in error_message_str or "Admission application is missing a proposed password" in error_message_str or "Cannot approve: Proposed username" in error_message_str or "Failed to fetch details for newly created student" in error_message_str): # Check for new exceptions
             return jsonify({"error": error_message_str}), 400 # Return the specific data/validation error with 400
        # If it's another type of exception, return a generic 500 error
        return jsonify({"error": f"An unexpected error occurred during approval process: {type(e).__name__} - {e}"}), 500


@app.route('/admin/applications/<application_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_application_for_admin(user, application_id):
    """
    Deletes a specific admission application by application_id for admin view,
    setting FKs in related tables (admissionstatus) to NULL.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete applications."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the application exists ---
        # *** VERIFY 'admissionapplications' TABLE NAME AND 'application_id' COLUMN ***
        cur.execute("SELECT application_id FROM admissionapplications WHERE application_id = %s;", (application_id,))
        app_exists = cur.fetchone()
        if app_exists is None:
            return jsonify({"error": "Application not found."}), 404


        # --- Delete Related Records (Set FKs to NULL) ---

        # 1. Set application_id to NULL for records in admissionstatus linked to this application
        #    This assumes admissionstatus has a FK named application_id referencing admissionapplications.
        #    We previously made admissionstatus.application_id nullable.
        # *** VERIFY 'admissionstatus' TABLE NAME AND 'application_id' COLUMN ***
        sql_nullify_status_application = "UPDATE admissionstatus SET application_id = NULL WHERE application_id = %s;"
        cur.execute(sql_nullify_status_application, (application_id,))
        print(f"Set application_id to NULL for {cur.rowcount} admission status records linked to application {application_id}") # Debug print

        # Add updates for any other tables that directly reference admissionapplications if they exist
        # e.g., if a 'student_documents' table had a foreign key application_id -> admissionapplications.application_id


        # --- Finally, Delete the Admission Application Record ---
        sql_delete_application = "DELETE FROM admissionapplications WHERE application_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_application, (application_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # This case should ideally not be reached if app_exists check passed,
             # but included as a safeguard.
             return jsonify({"error": "Application found but could not be deleted."}), 500

        conn.commit()
        # Message adjusted as we updated related records
        return jsonify({"message": f"Admission application {application_id} and linked status records updated successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during application deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled or wasn't set to NULL!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during application deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/course-assignments', methods=['GET'])
@login_required # Protect this route
def list_all_course_assignments(user):
    """
    Retrieves a list of all course assignments.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the course assignment list."}), 403


    # --- Fetch All Course Assignments Data ---
    conn = None
    cur = None
    assignments_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all assignment details, join related tables for context
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                ca.assignment_id, -- Primary key
                ca.course_id,    -- FK to courses
                c.course_code,   -- From joined courses
                c.course_title,  -- From joined courses
                ca.lecturer_id,  -- FK to lecturers
                l.first_name AS lecturer_first_name, -- From joined lecturers
                l.last_name AS lecturer_last_name,   -- From joined lecturers
                ca.academic_year_id, -- FK to academicyears
                ay.term_name AS academic_year_term, -- From joined academicyears
                ca.semester -- Assuming a semester column exists
                -- Include other columns if they exist in your coursesassignedtolecturers table (e.g., start_date, end_date for assignment period)
            FROM coursesassignedtolecturers ca -- *** Use the correct table name ***
            JOIN courses c ON ca.course_id = c.course_id -- *** Join courses table ***
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id -- *** Join lecturers table ***
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            ORDER BY ay.year DESC, ca.semester, c.course_code; -- Order by year, semester, course code
        """
        # Note: Adjust column names (assignment_id, course_id, lecturer_id, academic_year_id, semester,
        # course_code, course_title, first_name, last_name, term_name) if your schema is different.
        # If a column or table doesn't exist, remove it from the SELECT list and JOIN clauses.
        # Assumes lecturer name is in first_name, last_name columns.

        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        assignments_list = cur.fetchall()

        return jsonify(assignments_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching course assignment list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching course assignment list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/course-assignments/<assignment_id>', methods=['GET'])
@login_required # Protect this route
def get_course_assignment_details_for_admin(user, assignment_id):
    """
    Retrieves details of a specific course assignment by assignment_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view course assignment details."}), 403


    # --- Fetch Specific Course Assignment Data ---
    conn = None
    cur = None
    assignment_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant assignment details for the given assignment_id, join related tables
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                ca.assignment_id, -- Primary key
                ca.course_id,    -- FK
                c.course_code,   -- From joined courses
                c.course_title,  -- From joined courses
                ca.lecturer_id,  -- FK
                l.first_name AS lecturer_first_name, -- From joined lecturers
                l.last_name AS lecturer_last_name,   -- From joined lecturers
                ca.academic_year_id, -- FK
                ay.term_name AS academic_year_term, -- From joined academicyears
                ca.semester -- Assuming a semester column exists
                -- Include other columns if they exist in your coursesassignedtolecturers table
            FROM coursesassignedtolecturers ca -- *** Use the correct table name ***
            JOIN courses c ON ca.course_id = c.course_id -- *** Join courses table ***
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id -- *** Join lecturers table ***
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            WHERE ca.assignment_id = %s; -- *** Filter by the assignment_id from the URL path ***
        """
        # Note: Adjust column names and table names if your schema is different.


        # Use the assignment_id from the URL path parameter
        cur.execute(sql, (assignment_id,))

        assignment_details = cur.fetchone()

        if assignment_details is None:
            # Assignment with the given ID not found
            return jsonify({"error": "Course assignment not found."}), 404 # 404 Not Found

        return jsonify(assignment_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific course assignment details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific course assignment details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/course-assignments', methods=['POST'])
@login_required # Protect this route
def create_course_assignment_for_admin(user):
    """
    Creates a new course assignment via admin dashboard.
    Requires 'admin' role.
    Accepts new assignment data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create course assignments."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on a typical schema for course assignments linking to Course, Lecturer, Academic Year, and Semester.
    # Assuming assignment_id is provided by the user/frontend for creation.
    # *** VERIFY your required columns and if assignment_id is auto-generated or provided ***
    required_fields = [
        'assignment_id',     # Assuming PK is provided
        'course_id',         # FK to courses
        'lecturer_id',       # FK to lecturers
        'academic_year_id',  # FK to academicyears
        'semester'           # Assuming semester is required
    ]
    # Add other required columns if any

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    assignment_id = data.get('assignment_id') # Provided PK
    course_id = data.get('course_id')
    lecturer_id = data.get('lecturer_id')
    academic_year_id = data.get('academic_year_id')
    semester = data.get('semester')
    # Extract other optional/nullable fields if any


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for inserts/updates

        # --- Basic Validation ---
        # Check for duplicate assignment_id (assuming it should be unique PK)
        # *** VERIFY your PK column name and if it's auto-generated ***
        cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE assignment_id = %s;", (assignment_id,))
        if cur.fetchone():
             return jsonify({"error": f"Assignment ID '{assignment_id}' already exists."}), 409 # 409 Conflict

        # Validate FKs exist (recommended before inserting)
        # Check if course_id is valid
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (course_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Course ID '{course_id}' not found."}), 400

        # Check if lecturer_id is valid
        cur.execute("SELECT lecturer_id FROM lecturers WHERE lecturer_id = %s;", (lecturer_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Lecturer ID '{lecturer_id}' not found."}), 400

        # Check if academic_year_id is valid
        cur.execute("SELECT academic_year_id FROM academicyears WHERE academic_year_id = %s;", (academic_year_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Academic Year ID '{academic_year_id}' not found."}), 400

        # Optional: Check for potential duplicate assignment based on FKs + semester
        # E.g., only one lecturer assigned to a course in a specific semester/year?
        # cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE course_id = %s AND lecturer_id = %s AND academic_year_id = %s AND semester = %s;", (course_id, lecturer_id, academic_year_id, semester))
        # if cur.fetchone():
        #      return jsonify({"error": "Assignment for this Course, Lecturer, Year, and Semester already exists."}), 409


        # --- Create Course Assignment Record ---
        # Insert into the coursesassignedtolecturers table
        # *** VERIFY column names: assignment_id, course_id, lecturer_id, academic_year_id, semester ***
        sql_insert_assignment = """
            INSERT INTO coursesassignedtolecturers (assignment_id, course_id, lecturer_id, academic_year_id, semester) -- *** Adjust column names ***
            VALUES (%s, %s, %s, %s, %s);
            -- No RETURNING needed if PK is provided by user/frontend
        """
        execute_values = (assignment_id, course_id, lecturer_id, academic_year_id, semester)
        # Include other nullable/optional fields in INSERT and VALUES if needed


        cur.execute(sql_insert_assignment, execute_values)
        # No new_assignment_id = cur.fetchone()[0] needed if PK is provided


        conn.commit()

        # Return success message and the created ID
        return jsonify({
            "message": f"Course assignment '{assignment_id}' created successfully!",
            "assignment_id": assignment_id # Return the provided ID
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during course assignment creation: {e}")
        # This could happen due to duplicate assignment_id, or FK violation if not validated manually
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course assignment creation: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course assignment creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/course-assignments/<assignment_id>', methods=['PUT'])
@login_required # Protect this route
def update_course_assignment_details_for_admin(user, assignment_id):
    """
    Updates details of a specific course assignment by assignment_id for admin view.
    Requires 'admin' role.
    Accepts updated assignment data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update course assignment details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your coursesassignedtolecturers schema (Exclude assignment_id as it's the PK)
    updatable_fields = [
        'course_id',         # FK to courses
        'lecturer_id',       # FK to lecturers
        'academic_year_id',  # FK to academicyears
        'semester'           # Assuming semester is updatable
    ]
    # Add other updatable columns if any

    update_data = {}
    for field in updatable_fields:
        # Only include fields present in the request body and not None/empty string if required by schema
        if field in data and data.get(field) is not None: # Allow None if nullable
            # Basic check for required fields if provided in update data
            if field in ['course_id', 'lecturer_id', 'academic_year_id', 'semester']: # These might be required
                 if not data.get(field):
                      return jsonify({"error": f"Required field '{field}' cannot be empty if provided for update."}), 400

            update_data[field] = data[field]


    # If no updatable fields are provided, nothing to do
    if not update_data:
        return jsonify({"message": "No updatable fields provided in the request body."}), 200 # Or 400


    conn = None
    cur = None # Initialize cur to None
    cur_fetch = None # Initialize cur_fetch to None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # *** Initialize main cursor HERE, inside the try block ***
        # cur_fetch will be initialized later if needed within the try block

        # --- First, verify if the assignment exists ---
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'assignment_id' COLUMN ***
        cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE assignment_id = %s;", (assignment_id,))
        assignment_exists = cur.fetchone()
        if assignment_exists is None:
            return jsonify({"error": "Course assignment not found."}), 404


        # --- Basic Validation (Check for FK existence if they are updated) ---
        # Check if course_id is valid if it's being updated
        if 'course_id' in update_data:
            cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (update_data['course_id'],))
            if not cur.fetchone():
                 return jsonify({"error": f"Course ID '{update_data['course_id']}' not found."}), 400

        # Check if lecturer_id is valid if it's being updated
        if 'lecturer_id' in update_data:
            cur.execute("SELECT lecturer_id FROM lecturers WHERE lecturer_id = %s;", (update_data['lecturer_id'],))
            if not cur.fetchone():
                 return jsonify({"error": f"Lecturer ID '{update_data['lecturer_id']}' not found."}), 400

        # Check if academic_year_id is valid if it's being updated
        if 'academic_year_id' in update_data:
            cur.execute("SELECT academic_year_id FROM academicyears WHERE academic_year_id = %s;", (update_data['academic_year_id'],))
            if not cur.fetchone():
                 return jsonify({"error": f"Academic Year ID '{update_data['academic_year_id']}' not found."}), 400

        # Optional: Check for potential duplicate assignment after update (same course, lecturer, year, semester)
        # This requires checking against existing assignments *excluding* the current one being updated
        # Check if all relevant fields for uniqueness are in the update_data OR fetch current values to check uniqueness
        # This can be complex. For simplicity, uncomment and adjust if needed based on your exact uniqueness rules
        # if all(f in update_data for f in ['course_id', 'lecturer_id', 'academic_year_id', 'semester']):
        #      cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE course_id = %s AND lecturer_id = %s AND academic_year_id = %s AND semester = %s AND assignment_id != %s;",
        #                   (update_data['course_id'], update_data['lecturer_id'], update_data['academic_year_id'], update_data['semester'], assignment_id))
        #      if cur.fetchone():
        #           return jsonify({"error": "Assignment for this Course, Lecturer, Year, and Semester already exists."}), 409


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200 # Should already be caught


        sql_update = f"""
            UPDATE coursesassignedtolecturers -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE assignment_id = %s; -- *** Filter by the assignment_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [assignment_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Course assignment found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()

        # Fetch and return the updated assignment details including joined data
        cur_fetch = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor
        sql_fetch = """
            SELECT
                ca.assignment_id, ca.course_id, c.course_code, c.course_title,
                ca.lecturer_id, l.first_name AS lecturer_first_name, l.last_name AS lecturer_last_name,
                ca.academic_year_id, ay.term_name AS academic_year_term, ca.semester
                -- Include other columns if they exist
            FROM coursesassignedtolecturers ca
            JOIN courses c ON ca.course_id = c.course_id
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id
            WHERE ca.assignment_id = %s;
        """
        cur_fetch.execute(sql_fetch, (assignment_id,))
        updated_assignment_details = cur_fetch.fetchone()
        # cur_fetch.close() # Close this cursor (handled in finally if using separate cursor)


        return jsonify(updated_assignment_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during course assignment update: {e}")
        # This could happen if FK constraints fail despite validation, or if a unique constraint is violated (e.g., duplicate assignment combination)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course assignment update: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course assignment update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if cur_fetch: # Close the fetch cursor if it was opened
             cur_fetch.close()
        if conn:
            conn.close()

@app.route('/admin/course-assignments/<assignment_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_course_assignment_for_admin(user, assignment_id):
    """
    Deletes a specific course assignment by assignment_id for admin view,
    including associated records based on ON DELETE NO ACTION schema.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete course assignments."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the assignment exists ---
        # *** VERIFY 'coursesassignedtolecturers' TABLE NAME AND 'assignment_id' COLUMN ***
        cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE assignment_id = %s;", (assignment_id,))
        assignment_exists = cur.fetchone()
        if assignment_exists is None:
            return jsonify({"error": "Course assignment not found."}), 404


        # --- Delete Related Records (Order is crucial with NO ACTION!) ---

        # 1. Find all session_ids for this assignment
        # *** VERIFY 'attendancesessions' TABLE NAME AND 'assignment_id', 'session_id' COLUMNS ***
        sql_get_sessions = """
            SELECT session_id FROM attendancesessions WHERE assignment_id = %s;
        """
        cur.execute(sql_get_sessions, (assignment_id,))
        session_ids_rows = cur.fetchall()
        # Extract session IDs into a list
        session_ids = [row[0] for row in session_ids_rows]
        print(f"Found {len(session_ids)} sessions for assignment {assignment_id}: {session_ids}") # Debug print

        # 2. If sessions exist, delete attendance records for these sessions
        # *** VERIFY 'attendancerecords' TABLE NAME AND 'session_id' COLUMN ***
        if session_ids:
            sql_delete_attendance = """
                DELETE FROM attendancerecords WHERE session_id IN %s;
            """
             # Execute with tuple of session_ids for the IN clause
            cur.execute(sql_delete_attendance, (tuple(session_ids),))
            print(f"Deleted {cur.rowcount} attendance records for sessions") # Debug print

        # 3. Delete the sessions themselves (if sessions exist)
        # *** VERIFY 'attendancesessions' TABLE NAME ***
        sql_delete_sessions = "DELETE FROM attendancesessions WHERE assignment_id = %s;" # Delete sessions linked to this assignment
        cur.execute(sql_delete_sessions, (assignment_id,))
        print(f"Deleted {cur.rowcount} sessions for assignment") # Debug print

        # Add deletions for any other tables that directly reference coursesassignedtolecturers if they exist


        # --- Finally, Delete the Course Assignment Record ---
        sql_delete_assignment = "DELETE FROM coursesassignedtolecturers WHERE assignment_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_assignment, (assignment_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if assignment_exists check passed
             return jsonify({"error": "Course assignment found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Course assignment {assignment_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during course assignment deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during course assignment deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/attendance-sessions', methods=['GET'])
@login_required # Protect this route
def list_all_attendance_sessions(user):
    """
    Retrieves a list of all attendance sessions.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view the attendance session list."}), 403


    # --- Fetch All Attendance Sessions Data ---
    conn = None
    cur = None
    sessions_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all session details, join related tables for context
        # Join through coursesassignedtolecturers to get Course, Lecturer, Year details
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES based on schema ***
        sql = """
            SELECT
                ats.session_id,      -- Primary key
                ats.assignment_id,   -- FK to coursesassignedtolecturers
                ca.semester,         -- From joined coursesassignedtolecturers
                ca.course_id,        -- FK to courses (via ca)
                c.course_code,       -- From joined courses
                c.course_title,      -- From joined courses
                ca.lecturer_id,      -- FK to lecturers (via ca)
                l.first_name AS lecturer_first_name, -- From joined lecturers
                l.last_name AS lecturer_last_name,   -- From joined lecturers
                ca.academic_year_id, -- FK to academicyears (via ca)
                ay.term_name AS academic_year_term, -- From joined academicyears
                ats.session_datetime, -- *** CORRECTED COLUMN NAME based on schema ***
                ats.duration_minutes, -- Include duration
                ats.location          -- Include location
                -- Include other columns if they exist in your attendancesessions table (e.g., qr_code_expiry_time, created_at)
            FROM attendancesessions ats -- *** Use the correct table name ***
            JOIN coursesassignedtolecturers ca ON ats.assignment_id = ca.assignment_id -- *** Join coursesassignedtolecturers ***
            JOIN courses c ON ca.course_id = c.course_id -- *** Join courses table ***
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id -- *** Join lecturers table ***
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            ORDER BY ats.session_datetime DESC; -- *** CORRECTED ORDER BY column ***
        """
        # Removed: ats.session_date, ats.start_time, ats.end_time
        # Added: ats.duration_minutes, ats.location (based on schema output)


        # No WHERE clause needed to filter, as admin sees all
        cur.execute(sql)

        sessions_list = cur.fetchall()

        # Optional: Convert timestamps to string format for JSON if needed
        # for session in sessions_list:
        #     if session.get('session_datetime'):
        #         # Assuming session_datetime is a datetime object
        #         session['session_datetime'] = session['session_datetime'].isoformat()


        return jsonify(sessions_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching attendance session list: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching attendance session list: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-sessions/<session_id>', methods=['GET'])
@login_required # Protect this route
def get_attendance_session_details_for_admin(user, session_id):
    """
    Retrieves details of a specific attendance session by session_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view attendance session details."}), 403


    # --- Fetch Specific Attendance Session Data ---
    conn = None
    cur = None
    session_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant session details for the given session_id, join related tables
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES based on schema ***
        sql = """
            SELECT
                ats.session_id,      -- Primary key
                ats.assignment_id,   -- FK to coursesassignedtolecturers
                ca.semester,         -- From joined coursesassignedtolecturers
                ca.course_id,        -- FK to courses (via ca)
                c.course_code,       -- From joined courses
                c.course_title,      -- From joined courses
                ca.lecturer_id,      -- FK to lecturers (via ca)
                l.first_name AS lecturer_first_name, -- From joined lecturers
                l.last_name AS lecturer_last_name,   -- From joined lecturers
                ca.academic_year_id, -- FK to academicyears (via ca)
                ay.term_name AS academic_year_term, -- From joined academicyears
                ats.session_datetime, -- CORRECTED COLUMN NAME based on schema
                ats.duration_minutes, -- Include duration
                ats.location,         -- Include location
                ats.qr_code_expiry_time, -- Include QR code expiry time
                ats.created_at        -- Include creation timestamp
                -- Include other columns if they exist in your attendancesessions table
            FROM attendancesessions ats -- *** Use the correct table name ***
            JOIN coursesassignedtolecturers ca ON ats.assignment_id = ca.assignment_id -- *** Join coursesassignedtolecturers ***
            JOIN courses c ON ca.course_id = c.course_id -- *** Join courses table ***
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id -- *** Join lecturers table ***
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id -- *** Join academicyears table ***
            WHERE ats.session_id = %s; -- *** Filter by the session_id from the URL path ***
        """
        # Note: Adjust column names and table names if your schema is different.
        # Added qr_code_expiry_time and created_at based on your schema output


        # Use the session_id from the URL path parameter
        cur.execute(sql, (session_id,))

        session_details = cur.fetchone()

        if session_details is None:
            # Session with the given ID not found
            return jsonify({"error": "Attendance session not found."}), 404 # 404 Not Found

        # Optional: Convert timestamps to string format for JSON if needed
        # if session_details:
        #      if session_details.get('session_datetime'):
        #          session_details['session_datetime'] = session_details['session_datetime'].isoformat()
        #      if session_details.get('qr_code_expiry_time'):
        #          session_details['qr_code_expiry_time'] = session_details['qr_code_expiry_time'].isoformat()
        #      if session_details.get('created_at'):
        #          session_details['created_at'] = session_details['created_at'].isoformat()


        return jsonify(session_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific attendance session details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific attendance session details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-sessions', methods=['POST'])
@login_required # Protect this route
def create_attendance_session_for_admin(user):
    """
    Creates a new attendance session via admin dashboard.
    Requires 'admin' role.
    Accepts new session data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create attendance sessions."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your attendancesessions schema output (NOT NULL columns, excluding PK if auto-generated)
    # *** VERIFY your required columns and if session_id is auto-generated or provided ***
    required_fields = [
        #'session_id',      # Assuming PK is generated by trigger based on \d output
        'assignment_id',   # FK to coursesassignedtolecturers (NOT NULL)
        'session_datetime', # timestamp with time zone (NOT NULL)
        'duration_minutes', # integer (NOT NULL)
        'qr_code_expiry_time' # timestamp with time zone (NOT NULL)
    ]
    # location, created_at are nullable/have defaults.

    for field in required_fields:
        if field not in data or data.get(field) is None: # Check for presence and not None
             # For strings/IDs, you might want to check for empty strings too
             if isinstance(data.get(field), str) and not data.get(field):
                  return jsonify({"error": f"Missing or empty required field: {field}"}), 400
             # For numbers/dates, just check for None
             if data.get(field) is None:
                  return jsonify({"error": f"Missing required field: {field}"}), 400

    # Extract data
    # session_id is auto-generated
    assignment_id = data.get('assignment_id')
    session_datetime_str = data.get('session_datetime')
    duration_minutes = data.get('duration_minutes')
    qr_code_expiry_time_str = data.get('qr_code_expiry_time')
    location = data.get('location') # Optional/nullable


    # --- Basic Validation ---
    # Validate assignment_id exists (recommended before inserting)
    cur = None # Initialize cursor here
    conn = None # Initialize connection here
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE assignment_id = %s;", (assignment_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Assignment ID '{assignment_id}' not found."}), 400

        # Validate duration_minutes is a positive integer
        if not isinstance(duration_minutes, int) or duration_minutes <= 0:
            return jsonify({"error": "Duration minutes must be a positive integer."}), 400

        # Validate and parse timestamp fields
        try:
             # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
             # Use fromisoformat if you expect ISO 8601 strings
             session_datetime_obj = datetime.fromisoformat(session_datetime_str)
             qr_code_expiry_time_obj = datetime.fromisoformat(qr_code_expiry_time_str)
             # Handle potential timezone information if necessary for timestamp with time zone
             # If strings don't have timezone info, they'll be interpreted based on server/DB settings.
             # For simplicity, assuming they might be timezone-aware or naive consistently.

        except ValueError:
             return jsonify({"error": "Invalid timestamp format. Use YYYY-MM-DD HH:MM:SS or ISO 8601."}), 400

        # Optional: Check for potential duplicate sessions based on assignment_id and session_datetime?


        # --- Create Attendance Session Record ---
        # Insert into the attendancesessions table
        # Exclude session_id (generated by trigger)
        # Exclude created_at (has default)
        # Include all other columns based on schema output
        # *** VERIFY column names and order match your schema ***
        sql_insert_session = """
            INSERT INTO attendancesessions (assignment_id, session_datetime, duration_minutes, location, qr_code_expiry_time) -- *** Adjust column names ***
            VALUES (%s, %s, %s, %s, %s)
            RETURNING session_id; -- Get the generated ID
        """
        # Pass values matching the column order in INSERT
        execute_values = (
            assignment_id,
            session_datetime_obj, # Pass parsed datetime object
            duration_minutes,
            location, # Can be NULL if not provided
            qr_code_expiry_time_obj # Pass parsed datetime object
        )


        cur.execute(sql_insert_session, execute_values)
        new_session_id = cur.fetchone()[0]


        conn.commit()

        # Return success message and the created ID
        return jsonify({
            "message": f"Attendance session '{new_session_id}' created successfully!",
            "session_id": new_session_id # Return the generated ID
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance session creation: {e}")
        # This could happen if FK violation (should be caught by manual check) or other constraints
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during attendance session creation: {e}")
        # This could happen if data types are wrong or other DB issues
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance session creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-sessions/<session_id>', methods=['PUT'])
@login_required # Protect this route
def update_attendance_session_details_for_admin(user, session_id):
    """
    Updates details of a specific attendance session by session_id for admin view.
    Requires 'admin' role.
    Accepts updated session data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update attendance session details."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your attendancesessions schema output (Exclude session_id PK, created_at default)
    updatable_fields = [
        'assignment_id',      # FK to coursesassignedtolecturers (NOT NULL)
        'session_datetime',   # timestamp with time zone (NOT NULL)
        'duration_minutes',   # integer (NOT NULL)
        'location',           # character varying(255) (nullable)
        'qr_code_expiry_time' # timestamp with time zone (NOT NULL)
    ]

    update_data = {}
    # Use a separate dict for fields needing specific validation/parsing before adding to update_data
    validated_data = {}

    conn = None # Initialize connection here
    cur = None # Initialize cursor here
    cur_fetch = None # Cursor for fetching updated details


    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions


        # --- First, verify if the session exists ---
        # *** VERIFY 'attendancesessions' TABLE NAME AND 'session_id' COLUMN ***
        cur.execute("SELECT session_id FROM attendancesessions WHERE session_id = %s;", (session_id,))
        session_exists = cur.fetchone()
        if session_exists is None:
            return jsonify({"error": "Attendance session not found."}), 404


        # --- Validate and Prepare Updatable Fields ---
        for field in updatable_fields:
             if field in data: # Only process if the field is in the request body
                 value = data[field]

                 # Handle NOT NULL fields: ensure they are not None/empty string if provided for update
                 if field in ['assignment_id', 'session_datetime', 'duration_minutes', 'qr_code_expiry_time']:
                     if value is None or (isinstance(value, str) and not value): # Check for None or empty string
                         return jsonify({"error": f"Required field '{field}' cannot be null or empty if provided for update."}), 400

                 # Perform specific validation/parsing based on field
                 if field == 'assignment_id':
                     # Validate assignment_id exists if it's being updated
                     cur.execute("SELECT assignment_id FROM coursesassignedtolecturers WHERE assignment_id = %s;", (value,))
                     if not cur.fetchone():
                          return jsonify({"error": f"Assignment ID '{value}' not found."}), 400
                     validated_data[field] = value # Use the validated value

                 elif field == 'duration_minutes':
                     # Validate duration_minutes is a positive integer
                     if not isinstance(value, int) or value <= 0:
                         return jsonify({"error": "Duration minutes must be a positive integer."}), 400
                     validated_data[field] = value # Use the validated value

                 elif field in ['session_datetime', 'qr_code_expiry_time']:
                     # Validate and parse timestamp fields
                     try:
                          # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
                          # Use fromisoformat if you expect ISO 8601 strings
                          timestamp_obj = datetime.fromisoformat(value)
                          validated_data[field] = timestamp_obj # Use the parsed datetime object
                     except (ValueError, TypeError): # Catch TypeError if value is not a string
                          return jsonify({"error": f"Invalid timestamp format for '{field}'. Use-MM-DD HH:MM:SS or ISO 8601."}), 400

                 else:
                     # For other updatable fields (like 'location'), just add the value directly
                     validated_data[field] = value


        # Use the validated_data for the update
        update_data = validated_data

        # If no updatable fields were successfully validated/processed, nothing to do
        if not update_data:
             return jsonify({"message": "No valid updatable fields provided in the request body."}), 200


        # Optional: Check for potential duplicate sessions after update (e.g., same assignment and session_datetime?)
        # This requires checking against existing sessions *excluding* the current one being updated
        # if all(f in update_data for f in ['assignment_id', 'session_datetime']):
        #      cur.execute("SELECT session_id FROM attendancesessions WHERE assignment_id = %s AND session_datetime = %s AND session_id != %s;",
        #                   (update_data['assignment_id'], update_data['session_datetime'], session_id))
        #      if cur.fetchone():
        #           return jsonify({"error": "Attendance session for this Assignment and Datetime already exists."}), 409


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200 # Should already be caught


        sql_update = f"""
            UPDATE attendancesessions -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE session_id = %s; -- *** Filter by the session_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [session_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Attendance session found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()

        # Fetch and return the updated session details including joined data
        cur_fetch = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor
        sql_fetch = """
            SELECT
                ats.session_id, ats.assignment_id, ca.semester, ca.course_id, c.course_code, c.course_title,
                ca.lecturer_id, l.first_name AS lecturer_first_name, l.last_name AS lecturer_last_name,
                ca.academic_year_id, ay.term_name AS academic_year_term,
                ats.session_datetime, ats.duration_minutes, ats.location, ats.qr_code_expiry_time, ats.created_at
                -- Include other columns if they exist
            FROM attendancesessions ats
            JOIN coursesassignedtolecturers ca ON ats.assignment_id = ca.assignment_id
            JOIN courses c ON ca.course_id = c.course_id
            JOIN lecturers l ON ca.lecturer_id = l.lecturer_id
            JOIN academicyears ay ON ca.academic_year_id = ay.academic_year_id
            WHERE ats.session_id = %s;
        """
        cur_fetch.execute(sql_fetch, (session_id,))
        updated_session_details = cur_fetch.fetchone()
        # cur_fetch.close() # Handled in finally


        # Optional: Convert timestamps to string format for JSON if needed in response
        # if updated_session_details:
        #      if updated_session_details.get('session_datetime'):
        #          updated_session_details['session_datetime'] = updated_session_details['session_datetime'].isoformat()
        #      if updated_session_details.get('qr_code_expiry_time'):
        #          updated_session_details['qr_code_expiry_time'] = updated_session_details['qr_code_expiry_time'].isoformat()
        #      if updated_session_details.get('created_at'):
        #          updated_session_details['created_at'] = updated_session_details['created_at'].isoformat()


        return jsonify(updated_session_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance session update: {e}")
        # This could happen if FK constraints fail despite validation, or if a unique constraint is violated (e.g., duplicate session combination)
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except (psycopg2.Error, ValueError, TypeError) as e: # Catch DB errors and parsing errors
        if conn:
            conn.rollback()
        print(f"Database or data processing error during attendance session update: {e}")
        # Specific checks for e type might be needed for more granular error responses
        return jsonify({"error": f"Database or data processing error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance session update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if cur_fetch: # Close the fetch cursor if it was opened
             cur_fetch.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-sessions/<session_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_attendance_session_for_admin(user, session_id):
    """
    Deletes a specific attendance session by session_id for admin view,
    including associated attendance records based on ON DELETE NO ACTION schema.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete attendance sessions."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the session exists ---
        # *** VERIFY 'attendancesessions' TABLE NAME AND 'session_id' COLUMN ***
        cur.execute("SELECT session_id FROM attendancesessions WHERE session_id = %s;", (session_id,))
        session_exists = cur.fetchone()
        if session_exists is None:
            return jsonify({"error": "Attendance session not found."}), 404


        # --- Delete Related Records (Order is crucial with NO ACTION!) ---

        # 1. Delete attendance records for this session
        # *** VERIFY 'attendancerecords' TABLE NAME AND 'session_id' COLUMN ***
        sql_delete_attendance_records = "DELETE FROM attendancerecords WHERE session_id = %s;"
        cur.execute(sql_delete_attendance_records, (session_id,))
        print(f"Deleted {cur.rowcount} attendance records for session {session_id}") # Debug print

        # Add deletions for any other tables that directly reference attendancesessions if they exist


        # --- Finally, Delete the Attendance Session Record ---
        sql_delete_session = "DELETE FROM attendancesessions WHERE session_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_session, (session_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if session_exists check passed
             return jsonify({"error": "Attendance session found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Attendance session {session_id} and related records deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during attendance session deletion: {e}")
        # If you get a foreign key violation here, it means a referencing table wasn't handled!
        return jsonify({"error": f"Database error during deletion: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance session deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

@app.route('/admin/attendance-sessions/<session_id>/records', methods=['GET'])
@login_required # Protect this route
def list_attendance_records_for_session(user, session_id):
    """
    Retrieves a list of attendance records for a specific attendance session.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view attendance records."}), 403

    conn = None
    cur = None
    records_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # --- First, verify if the session exists ---
        # Good practice to ensure the session_id in the URL is valid
        # *** VERIFIED 'attendancesessions' TABLE NAME AND 'session_id' COLUMN ***
        cur.execute("SELECT session_id FROM attendancesessions WHERE session_id = %s;", (session_id,))
        session_exists = cur.fetchone()
        if session_exists is None:
            return jsonify({"error": "Attendance session not found."}), 404


        # --- Fetch Attendance Records for the Session ---
        # Select attendance record details, join students for name
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES based on schema ***
        sql = """
            SELECT
                atr.record_id,         -- *** CORRECTED PK COLUMN NAME ***
                atr.session_id,        -- FK to attendancesessions (should match URL)
                atr.student_id,        -- FK to students
                s.first_name AS student_first_name, -- From joined students
                s.last_name AS student_last_name,   -- From joined students
                atr.attendance_time,   -- *** CORRECTED TIMESTAMP COLUMN NAME ***
                atr.status,            -- Attendance status (e.g., 'Present', 'Absent', 'Late')
                atr.created_at         -- Timestamp when record was created
                -- Include other columns if they exist in your attendancerecords table (e.g., approved_by_lecturer_id)
            FROM attendancerecords atr -- *** Use the correct table name ***
            JOIN students s ON atr.student_id = s.student_id -- *** Join students table ***
            WHERE atr.session_id = %s -- *** Filter by the session_id from the URL path ***
            ORDER BY s.last_name, s.first_name; -- Order by student name
        """
        # Removed: atr.attendance_record_id, atr.recorded_at
        # Added/Corrected: atr.record_id, atr.attendance_time, atr.created_at


        # Use the session_id from the URL path parameter to filter
        cur.execute(sql, (session_id,))

        records_list = cur.fetchall()

        # Optional: Convert timestamps to string format for JSON if needed
        # for record in records_list:
        #     if record.get('attendance_time'):
        #         record['attendance_time'] = record['attendance_time'].isoformat()
        #     if record.get('created_at'):
        #         record['created_at'] = record['created_at'].isoformat()


        return jsonify(records_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching attendance records for session {session_id}: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching attendance records for session {session_id}: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-records/<record_id>', methods=['GET'])
@login_required # Protect this route
def get_attendance_record_details_for_admin(user, record_id):
    """
    Retrieves details of a specific attendance record by record_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_requester, role_requester, entity_id_requester = user # Unpack the requesting user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_requester != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view attendance record details."}), 403

    conn = None
    cur = None
    record_details = None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all relevant record details for the given record_id, join related tables
        # Join students and sessions for context
        # *** VERIFIED TABLE NAMES AND COLUMN NAMES based on schema ***
        sql = """
            SELECT
                atr.record_id,         -- Primary key
                atr.session_id,        -- FK to attendancesessions
                ats.session_datetime,  -- From joined attendancesessions
                ats.duration_minutes,  -- From joined attendancesessions
                ats.location AS session_location, -- From joined attendancesessions
                atr.student_id,        -- FK to students
                s.first_name AS student_first_name, -- From joined students
                s.last_name AS student_last_name,   -- From joined students
                atr.attendance_time,   -- The time attendance was recorded
                atr.status,            -- Attendance status
                atr.created_at         -- Timestamp when record was created
                -- Include other columns if they exist in your attendancerecords table
            FROM attendancerecords atr -- *** Use the correct table name ***
            JOIN attendancesessions ats ON atr.session_id = ats.session_id -- *** Join attendancesessions ***
            JOIN students s ON atr.student_id = s.student_id -- *** Join students table ***
            WHERE atr.record_id = %s; -- *** Filter by the record_id from the URL path ***
        """
        # Note: Adjust column names and table names if your schema is different.


        # Use the record_id from the URL path parameter
        cur.execute(sql, (record_id,))

        record_details = cur.fetchone()

        if record_details is None:
            # Record with the given ID not found
            return jsonify({"error": "Attendance record not found."}), 404 # 404 Not Found

        # Optional: Convert timestamps to string format for JSON if needed
        # if record_details:
        #      if record_details.get('session_datetime'):
        #          record_details['session_datetime'] = record_details['session_datetime'].isoformat()
        #      if record_details.get('attendance_time'):
        #          record_details['attendance_time'] = record_details['attendance_time'].isoformat()
        #      if record_details.get('created_at'):
        #          record_details['created_at'] = record_details['created_at'].isoformat()


        return jsonify(record_details), 200

    except psycopg2.Error as e:
        print(f"Database error fetching specific attendance record details: {e}")
        # Add checks for specific table/column names if needed
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching specific attendance record details: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-records', methods=['POST'])
@login_required # Protect this route
def create_attendance_record_for_admin(user):
    """
    Creates a new attendance record via admin dashboard.
    Requires 'admin' role.
    Accepts new record data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create attendance records."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on your attendancerecords schema output (NOT NULL columns, excluding PK if auto-generated)
    # *** VERIFY your required columns and if record_id is auto-generated or provided ***
    # record_id is generated by trigger based on \d output
    required_fields = [
        'session_id',        # FK to attendancesessions (NOT NULL)
        'student_id',        # FK to students (NOT NULL)
        'attendance_time',   # timestamp with time zone (NOT NULL)
        'status'             # character varying(50) (NOT NULL, but has default 'Present')
    ]
    # created_at has default.

    # Check required fields, but handle 'status' which has a default
    for field in required_fields:
        if field == 'status':
            # 'status' is required, but if not provided, will use default in INSERT
            # If provided, validate it's not null/empty later if needed, but let DB handle default for now
             continue # Skip required check here, handle below

        if field not in data or data.get(field) is None: # Check for presence and not None
             if isinstance(data.get(field), str) and not data.get(field): # Check for empty strings for string fields
                  return jsonify({"error": f"Missing or empty required field: {field}"}), 400
             if data.get(field) is None: # Check for None for non-string fields
                  return jsonify({"error": f"Missing required field: {field}"}), 400

    # Extract data - provide default for status if not in data
    # record_id is auto-generated
    session_id = data.get('session_id')
    student_id = data.get('student_id')
    attendance_time_str = data.get('attendance_time')
    status = data.get('status', 'Present') # Use default 'Present' if not provided
    # created_at will use the default CURRENT_TIMESTAMP


    # --- Basic Validation ---
    cur = None # Initialize cursor here
    conn = None # Initialize connection here
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Validate session_id exists (recommended before inserting)
        cur.execute("SELECT session_id FROM attendancesessions WHERE session_id = %s;", (session_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Attendance session ID '{session_id}' not found."}), 400

        # Validate student_id exists (recommended before inserting)
        cur.execute("SELECT student_id FROM students WHERE student_id = %s;", (student_id,))
        if not cur.fetchone():
             return jsonify({"error": f"Student ID '{student_id}' not found."}), 400

        # Validate and parse attendance_time timestamp
        try:
             # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
             # Use fromisoformat if you expect ISO 8601 strings
             attendance_time_obj = datetime.fromisoformat(attendance_time_str)
             # Handle potential timezone information if necessary
        except (ValueError, TypeError): # Catch TypeError if value is not a string
             return jsonify({"error": "Invalid attendance time format. Use-MM-DD HH:MM:SS or ISO 8601."}), 400

        # Check for duplicate (session_id, student_id) combination (UNIQUE constraint in schema)
        cur.execute("SELECT record_id FROM attendancerecords WHERE session_id = %s AND student_id = %s;", (session_id, student_id))
        if cur.fetchone():
             return jsonify({"error": f"Attendance record for session '{session_id}' and student '{student_id}' already exists."}), 409 # 409 Conflict


        # Optional: Validate status value against allowed list? (e.g., 'Present', 'Absent', 'Late', 'Excused')
        # allowed_statuses = ['Present', 'Absent', 'Late', 'Excused']
        # if status not in allowed_statuses:
        #      return jsonify({"error": f"Invalid attendance status: '{status}'. Must be one of {', '.join(allowed_statuses)}."}), 400


        # --- Create Attendance Record ---
        # Insert into the attendancerecords table
        # Exclude record_id (generated by trigger)
        # Exclude created_at (has default)
        # Include all other columns based on schema output
        # *** VERIFY column names and order match your schema ***
        sql_insert_record = """
            INSERT INTO attendancerecords (session_id, student_id, attendance_time, status) -- *** Adjust column names ***
            VALUES (%s, %s, %s, %s)
            RETURNING record_id; -- Get the generated ID
        """
        # Pass values matching the column order in INSERT
        execute_values = (
            session_id,
            student_id,
            attendance_time_obj, # Pass parsed datetime object
            status # Use provided status or 'Present' default
        )


        cur.execute(sql_insert_record, execute_values)
        new_record_id = cur.fetchone()[0]


        conn.commit()

        # Return success message and the created ID
        return jsonify({
            "message": f"Attendance record '{new_record_id}' created successfully!",
            "record_id": new_record_id # Return the generated ID
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance record creation: {e}")
        # This could happen due to duplicate (session_id, student_id) if not caught by manual check, or other constraints
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except (psycopg2.Error, ValueError, TypeError) as e: # Catch DB errors and parsing errors
        if conn:
            conn.rollback()
        print(f"Database or data processing error during attendance record creation: {e}")
        # Specific checks for e type might be needed for more granular error responses
        return jsonify({"error": f"Database or data processing error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance record creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-records/<record_id>', methods=['PUT'])
@login_required # Protect this route
def update_attendance_record_details_for_admin(user, record_id):
    """
    Updates details of a specific attendance record by record_id for admin view.
    Requires 'admin' role.
    Accepts updated record data in JSON request body.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can update attendance records."}), 403

    # --- Get Updated Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Extract fields that are allowed to be updated by admin ---
    # Based on your attendancerecords schema output (Exclude record_id PK, created_at default)
    updatable_fields = [
        'session_id',        # FK to attendancesessions (NOT NULL)
        'student_id',        # FK to students (NOT NULL)
        'attendance_time',   # timestamp with time zone (NOT NULL)
        'status'             # character varying(50) (NOT NULL, has default 'Present')
    ]
    # Add other updatable columns if any

    update_data = {}
    # Use a separate dict for fields needing specific validation/parsing before adding to update_data
    validated_data = {}

    conn = None # Initialize connection here
    cur = None # Initialize cursor here
    cur_fetch = None # Cursor for fetching updated details

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor for executions


        # --- First, verify if the record exists and get current FKs ---
        # We need current session_id and student_id to check for duplicate combinations if they are updated
        # *** VERIFY 'attendancerecords' TABLE NAME AND 'record_id', 'session_id', 'student_id' COLUMNS ***
        cur.execute("SELECT record_id, session_id, student_id FROM attendancerecords WHERE record_id = %s;", (record_id,))
        record_row = cur.fetchone()
        if record_row is None:
            return jsonify({"error": "Attendance record not found."}), 404

        # Extract current session_id and student_id
        current_session_id = record_row[1]
        current_student_id = record_row[2]


        # --- Validate and Prepare Updatable Fields ---
        for field in updatable_fields:
             if field in data: # Only process if the field is in the request body
                 value = data[field]

                 # Handle NOT NULL fields: ensure they are not None/empty string if provided for update
                 # These fields are NOT NULL in schema: session_id, student_id, attendance_time, status
                 # Status has default, but if provided, should be valid/non-empty
                 if field in ['session_id', 'student_id', 'attendance_time', 'status']:
                     if value is None or (isinstance(value, str) and not value): # Check for None or empty string
                         return jsonify({"error": f"Required field '{field}' cannot be null or empty if provided for update."}), 400

                 # Perform specific validation/parsing based on field
                 if field == 'session_id':
                     # Validate session_id exists if it's being updated
                     cur.execute("SELECT session_id FROM attendancesessions WHERE session_id = %s;", (value,))
                     if not cur.fetchone():
                          return jsonify({"error": f"Attendance session ID '{value}' not found."}), 400
                     validated_data[field] = value # Use the validated value

                 elif field == 'student_id':
                     # Validate student_id exists if it's being updated
                     cur.execute("SELECT student_id FROM students WHERE student_id = %s;", (value,))
                     if not cur.fetchone():
                          return jsonify({"error": f"Student ID '{value}' not found."}), 400
                     validated_data[field] = value # Use the validated value

                 elif field == 'attendance_time':
                     # Validate and parse timestamp field
                     try:
                          # Assuming format 'YYYY-MM-DD HH:MM:SS' or compatible ISO format
                          # Use fromisoformat if you expect ISO 8601 strings
                          timestamp_obj = datetime.fromisoformat(value)
                          validated_data[field] = timestamp_obj # Use the parsed datetime object
                     except (ValueError, TypeError): # Catch TypeError if value is not a string
                          return jsonify({"error": f"Invalid timestamp format for '{field}'. Use-MM-DD HH:MM:SS or ISO 8601."}), 400

                 elif field == 'status':
                     # Optional: Validate status value against allowed list? (e.g., 'Present', 'Absent', 'Late', 'Excused')
                     # allowed_statuses = ['Present', 'Absent', 'Late', 'Excused']
                     # if value not in allowed_statuses:
                     #      return jsonify({"error": f"Invalid attendance status: '{value}'. Must be one of {', '.join(allowed_statuses)}."}), 400
                     validated_data[field] = value # Use the provided status

                 else:
                     # For other updatable fields, just add the value directly
                     validated_data[field] = value


        # Use the validated_data for the update
        update_data = validated_data

        # If no updatable fields were successfully validated/processed, nothing to do
        if not update_data:
             return jsonify({"message": "No valid updatable fields provided in the request body."}), 200


        # --- Check for Unique Constraint Violation BEFORE Update ---
        # Check if the combination of session_id and student_id is changing AND if the new combination already exists for *another* record
        # Determine the session_id and student_id values that will be used for the update:
        # Use value from update_data if provided, otherwise use the current value from the database
        potential_new_session_id = update_data.get('session_id', current_session_id)
        potential_new_student_id = update_data.get('student_id', current_student_id)

        # Only check for duplicates if either session_id or student_id was included in the update data
        if 'session_id' in update_data or 'student_id' in update_data:
             cur.execute(
                  "SELECT record_id FROM attendancerecords WHERE session_id = %s AND student_id = %s AND record_id != %s;",
                  (potential_new_session_id, potential_new_student_id, record_id)
              )
             if cur.fetchone():
                  return jsonify({"error": f"Attendance record for session '{potential_new_session_id}' and student '{potential_new_student_id}' already exists."}), 409 # 409 Conflict


        # --- Construct and Execute the UPDATE SQL Query ---
        set_clauses = [f"{field} = %s" for field in update_data.keys()]
        if not set_clauses:
             return jsonify({"message": "No updatable fields to set."}), 200 # Should already be caught


        sql_update = f"""
            UPDATE attendancerecords -- *** Use the correct table name ***
            SET {', '.join(set_clauses)}
            WHERE record_id = %s; -- *** Filter by the record_id from the URL path ***
        """
        execute_values = list(update_data.values()) + [record_id]

        cur.execute(sql_update, execute_values)

        if cur.rowcount == 0:
             return jsonify({"message": "Attendance record found, but no changes were applied (data might be the same or invalid fields provided)."}), 200


        conn.commit()

        # Fetch and return the updated record details including joined data
        cur_fetch = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Use RealDictCursor
        sql_fetch = """
            SELECT
                atr.record_id, atr.session_id, ats.session_datetime, ats.duration_minutes, ats.location AS session_location,
                atr.student_id, s.first_name AS student_first_name, s.last_name AS student_last_name,
                atr.attendance_time, atr.status, atr.created_at
                -- Include other columns if they exist
            FROM attendancerecords atr
            JOIN attendancesessions ats ON atr.session_id = ats.session_id
            JOIN students s ON atr.student_id = s.student_id
            WHERE atr.record_id = %s;
        """
        cur_fetch.execute(sql_fetch, (record_id,))
        updated_record_details = cur_fetch.fetchone()
        # cur_fetch.close() # Handled in finally


        # Optional: Convert timestamps to string format for JSON if needed in response
        # if updated_record_details:
        #      if updated_record_details.get('session_datetime'):
        #          updated_record_details['session_datetime'] = updated_record_details['session_datetime'].isoformat()
        #      if updated_record_details.get('attendance_time'):
        #          updated_record_details['attendance_time'] = updated_record_details['attendance_time'].isoformat()
        #      if updated_record_details.get('created_at'):
        #          updated_record_details['created_at'] = updated_record_details['created_at'].isoformat()


        return jsonify(updated_record_details), 200 # Return updated details


    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance record update: {e}")
        # This could happen if FK constraints fail despite validation, or if the unique constraint is violated
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except (psycopg2.Error, ValueError, TypeError) as e: # Catch DB errors and parsing errors
        if conn:
            conn.rollback()
        print(f"Database or data processing error during attendance record update: {e}")
        # Specific checks for e type might be needed for more granular error responses
        return jsonify({"error": f"Database or data processing error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance record update: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if cur_fetch: # Close the fetch cursor if it was opened
             cur_fetch.close()
        if conn:
            conn.close()

@app.route('/admin/attendance-records/<record_id>', methods=['DELETE'])
@login_required # Protect this route
def delete_attendance_record_for_admin(user, record_id):
    """
    Deletes a specific attendance record by record_id for admin view.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can delete attendance records."}), 403


    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor() # Standard cursor

        # --- First, verify if the record exists ---
        # *** VERIFY 'attendancerecord s' TABLE NAME AND 'record_id' COLUMN ***
        cur.execute("SELECT record_id FROM attendancerecords WHERE record_id = %s;", (record_id,))
        record_exists = cur.fetchone()
        if record_exists is None:
            return jsonify({"error": "Attendance record not found."}), 404


        # --- Delete the Attendance Record ---
        # No other tables reference attendance records, so direct deletion is fine
        sql_delete_record = "DELETE FROM attendancerecords WHERE record_id = %s;" # *** Use the correct table name ***
        cur.execute(sql_delete_record, (record_id,))

        if cur.rowcount == 0:
             if conn:
                 conn.rollback()
             # Should not happen if record_exists check passed
             return jsonify({"error": "Attendance record found but could not be deleted."}), 500

        conn.commit()
        return jsonify({"message": f"Attendance record {record_id} deleted successfully."}), 200 # Or 204 No Content

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during attendance record deletion: {e}")
        # This shouldn't happen if no tables reference attendancerecords, but included for safety
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during attendance record deletion: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during attendance record deletion: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

####################################################################################

# --- Route that enables admin to post a notificatin
@app.route('/admin/notifications', methods=['POST'])
@login_required # Protect this route
def create_notification_for_admin(user):
    """
    Creates a new notification via admin dashboard.
    Requires 'admin' role.
    Accepts notification data in JSON request body.
    Admins can target 'All', 'Department', or 'Course'.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can create notifications."}), 403

    # --- Get Data from Request Body ---
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()

    # --- Validate Required Fields ---
    # Based on notifications schema (excluding auto-generated/default PK and created_at)
    required_fields = ['title', 'message', 'target_role']

    for field in required_fields:
        if field not in data or not data.get(field): # Check for presence and non-empty string
            return jsonify({"error": f"Missing or empty required field: {field}"}), 400

    # Extract data
    title = data.get('title')
    message = data.get('message')
    target_role = data.get('target_role')
    target_department_id = data.get('target_department_id') # Nullable
    target_course_id = data.get('target_course_id')       # Nullable

    # --- Validate target_role and associated IDs ---
    allowed_target_roles_admin = ['All', 'Student', 'Lecturer', 'Department', 'Course'] # Admin can target broadly
    if target_role not in allowed_target_roles_admin:
        return jsonify({"error": f"Invalid target_role '{target_role}'. Allowed roles for admin: {', '.join(allowed_target_roles_admin)}."}), 400

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # Validate FKs based on target_role
        if target_role == 'Department':
             if not target_department_id or not isinstance(target_department_id, str):
                  return jsonify({"error": "target_department_id is required and must be a string for target_role 'Department'."}), 400
             # Check if department exists
             cur.execute("SELECT department_id FROM departments WHERE department_id = %s;", (target_department_id,))
             if not cur.fetchone():
                  return jsonify({"error": f"Department ID '{target_department_id}' not found."}), 400
             # Ensure course ID is null for Department target
             if target_course_id is not None:
                  return jsonify({"error": "target_course_id must be null for target_role 'Department'."}), 400

        elif target_role == 'Course':
             if not target_course_id or not isinstance(target_course_id, str):
                  return jsonify({"error": "target_course_id is required and must be a string for target_role 'Course'."}), 400
             # Check if course exists
             cur.execute("SELECT course_id FROM courses WHERE course_id = %s;", (target_course_id,))
             if not cur.fetchone():
                  return jsonify({"error": f"Course ID '{target_course_id}' not found."}), 400
             # Ensure department ID is null for Course target
             if target_department_id is not None:
                  return jsonify({"error": "target_department_id must be null for target_role 'Course'."}), 400

        else: # target_role is 'All', 'Student', or 'Lecturer'
             # Ensure department and course IDs are null
             if target_department_id is not None or target_course_id is not None:
                  return jsonify({"error": "target_department_id and target_course_id must be null for target_role 'All', 'Student', or 'Lecturer'."}), 400


        # --- Create Notification Record ---
        # Insert into the notifications table
        # Exclude notification_id (generated by trigger/UUID)
        # Exclude created_at (has default)
        # *** VERIFY column names and order match your schema ***
        sql_insert_notification = """
            INSERT INTO notifications (title, message, created_by_user_account_id, target_role, target_department_id, target_course_id) -- *** Adjust column names ***
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING notification_id; -- Get the generated ID
        """
        execute_values = (
            title,
            message,
            user_account_id_admin, # Use the user_account_id from the logged-in admin
            target_role,
            target_department_id,
            target_course_id
        )

        cur.execute(sql_insert_notification, execute_values)
        new_notification_id = cur.fetchone()[0]

        conn.commit()

        return jsonify({
            "message": f"Notification '{new_notification_id}' created successfully!",
            "notification_id": new_notification_id
        }), 201 # 201 Created

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"Database integrity error during notification creation: {e}")
        # This could happen due to FK violation if not caught by manual check or other constraints
        return jsonify({"error": f"Database integrity error: {e}"}), 409 # 409 Conflict

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error during notification creation: {e}")
        # This could happen if data types are wrong or other DB issues
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred during notification creation: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/notifications', methods=['GET'])
@login_required # Protect this route
def list_all_notifications_for_admin(user):
    """
    Retrieves a list of all notifications for admin view.
    Requires 'admin' role.
    """
    user_account_id_admin, role_admin, entity_id_admin = user # Unpack the admin user tuple

    # --- Role Check: Ensure only admins can access this route ---
    if role_admin != 'admin':
        return jsonify({"error": "Access forbidden. Only admins can view all notifications."}), 403


    # --- Fetch All Notifications Data ---
    conn = None
    cur = None
    notifications_list = []

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Return rows as dictionaries

        # Select all notification details
        # Join useraccounts to show who created it (username and role)
        # Left Join departments and courses to show target names if applicable
        # *** VERIFY TABLE NAMES AND COLUMN NAMES ***
        sql = """
            SELECT
                n.notification_id,
                n.title,
                n.message,
                n.created_at,
                n.created_by_user_account_id,
                ua.username AS creator_username, -- Creator's username
                ua.role AS creator_role,        -- Creator's role
                n.target_role,                  -- The role/type targeted
                n.target_department_id,         -- Targeted department FK
                d.department_name AS target_department_name, -- Targeted department name
                n.target_course_id,             -- Targeted course FK
                c.course_code AS target_course_code,       -- Targeted course code
                c.course_title AS target_course_title      -- Targeted course title
                -- Include other columns from notifications if needed
            FROM notifications n -- *** Use the correct table name ***
            JOIN useraccounts ua ON n.created_by_user_account_id = ua.user_account_id -- *** Join useraccounts table ***
            LEFT JOIN departments d ON n.target_department_id = d.department_id -- *** Left Join departments (target may be null) ***
            LEFT JOIN courses c ON n.target_course_id = c.course_id -- *** Left Join courses (target may be null) ***
            ORDER BY n.created_at DESC; -- Order by most recent first
        """
        # Note: Adjust column names and table names if your schema is different.


        # No WHERE clause needed to filter by target, as admin sees all
        cur.execute(sql)

        notifications_list = cur.fetchall()

        # Optional: Convert timestamps to string format for JSON if needed
        # for notification in notifications_list:
        #     if notification.get('created_at'):
        #         notification['created_at'] = notification['created_at'].isoformat()


        return jsonify(notifications_list), 200

    except psycopg2.Error as e:
        print(f"Database error fetching all notifications: {e}")
        # Add checks for specific table/column names if needed
        error_message = str(e)
        if "relation \"" in error_message or "column \"" in error_message or "missing FROM-clause entry for table" in error_message:
            return jsonify({"error": "Configuration error: Database query error. Check table/column names and aliases."}), 500
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred fetching all notifications: {e}")
        return jsonify({"error": f"An unexpected internal error occurred: {type(e).__name__} - {e}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

######################################################################################################################################################

if __name__ == '__main__':
    app.run(debug=True)