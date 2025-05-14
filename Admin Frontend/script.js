// Configurable API base URL for local and Render environments
const API_BASE_URL = window.location.hostname === 'localhost' ? 'http://localhost:5000' : 'https://esas.onrender.com';

document.addEventListener('DOMContentLoaded', () => {
    // Retrieve JWT token from localStorage
    const token = localStorage.getItem('token');

    // Sidebar toggle for mobile
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.overlay');

    if (menuToggle && sidebar && overlay) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('visible');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
        });
    }

    // Section toggling and CRUD actions
    const sections = document.querySelectorAll('.content-section');
    const buttons = document.querySelectorAll('[data-action]');
    let currentDeleteId = null;

    buttons.forEach(button => {
        button.addEventListener('click', async () => {
            const action = button.getAttribute('data-action');
            sections.forEach(section => section.classList.add('hidden'));

            const sectionMap = {
                'show-add-application-form': 'add-application-section',
                'show-applications-list': 'applications-section',
                'show-update-status-form': 'update-status-section',
                'show-statuses-list': 'statuses-section',
                'show-add-student-form': 'add-student-section',
                'show-students-list': 'students-section',
                'show-add-lecturer-form': 'add-lecturer-section',
                'show-lecturers-list': 'lecturers-section',
                'show-add-course-form': 'add-course-section',
                'show-courses-list': 'courses-section',
                'show-add-department-form': 'add-department-section',
                'show-departments-list': 'departments-section',
                'show-add-faculty-form': 'add-faculty-section',
                'show-faculties-list': 'faculties-section',
                'show-add-session-form': 'add-session-section',
                'show-sessions-list': 'sessions-section',
                'show-add-attendance-form': 'add-attendance-section',
                'show-attendance-records-list': 'attendance-records-section',
                'show-add-notification-form': 'add-notification-section',
                'show-notifications-list': 'notifications-section',
                'show-add-academic-year-form': 'add-academic-year-section',
                'show-academic-years-list': 'academic-years-section',
                'show-add-administrator-form': 'add-administrator-section',
                'show-administrators-list': 'administrators-section'
            };

            if (sectionMap[action]) {
                document.getElementById(sectionMap[action])?.classList.remove('hidden');
            } else if (action === 'edit-application') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/applications/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const app = await response.json();
                    document.getElementById('edit-application-id').value = app.id || '';
                    document.getElementById('edit-applicant-name').value = app.applicant_name || '';
                    document.getElementById('edit-email').value = app.email || '';
                    document.getElementById('edit-program').value = app.program || '';
                    document.getElementById('edit-status').value = app.status || '';
                    document.getElementById('edit-submission-date').value = app.submission_date || '';
                    document.getElementById('edit-department').value = app.department_id || '';
                    document.getElementById('edit-application-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load application: ${err.message}`);
                }
            } else if (action === 'edit-student') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/students/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const student = await response.json();
                    document.getElementById('edit-student-id').value = student.id || '';
                    document.getElementById('edit-first-name').value = student.first_name || '';
                    document.getElementById('edit-last-name').value = student.last_name || '';
                    document.getElementById('edit-email').value = student.email || '';
                    document.getElementById('edit-contact-number').value = student.contact_number || '';
                    document.getElementById('edit-date-of-birth').value = student.date_of_birth || '';
                    document.getElementById('edit-gender').value = student.gender || '';
                    document.getElementById('edit-level').value = student.level || '';
                    document.getElementById('edit-department').value = student.department_id || '';
                    document.getElementById('edit-matric-no').value = student.matric_no || '';
                    document.getElementById('edit-intended-program').value = student.intended_program || '';
                    document.getElementById('edit-username').value = student.username || '';
                    document.getElementById('edit-student-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load student: ${err.message}`);
                }
            } else if (action === 'edit-lecturer') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/lecturers/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const lecturer = await response.json();
                    document.getElementById('edit-lecturer-id').value = lecturer.id || '';
                    document.getElementById('edit-first-name').value = lecturer.first_name || '';
                    document.getElementById('edit-last-name').value = lecturer.last_name || '';
                    document.getElementById('edit-email').value = lecturer.email || '';
                    document.getElementById('edit-contact-number').value = lecturer.contact_number || '';
                    document.getElementById('edit-date-of-birth').value = lecturer.date_of_birth || '';
                    document.getElementById('edit-gender').value = lecturer.gender || '';
                    document.getElementById('edit-position').value = lecturer.position || '';
                    document.getElementById('edit-department').value = lecturer.department_id || '';
                    document.getElementById('edit-staff-id').value = lecturer.staff_id || '';
                    document.getElementById('edit-username').value = lecturer.username || '';
                    document.getElementById('edit-lecturer-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load lecturer: ${err.message}`);
                }
            } else if (action === 'edit-course') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/courses/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const course = await response.json();
                    document.getElementById('edit-course-id').value = course.id || '';
                    document.getElementById('edit-course-code').value = course.course_code || '';
                    document.getElementById('edit-course-title').value = course.course_title || '';
                    document.getElementById('edit-department').value = course.department_id || '';
                    document.getElementById('edit-credits').value = course.credits || '';
                    document.getElementById('edit-level').value = course.level || '';
                    document.getElementById('edit-course-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load course: ${err.message}`);
                }
            } else if (action === 'edit-department') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/departments/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const department = await response.json();
                    document.getElementById('edit-department-id').value = department.id || '';
                    document.getElementById('edit-department-name').value = department.department_name || '';
                    document.getElementById('edit-faculty').value = department.faculty_id || '';
                    document.getElementById('edit-hod').value = department.head_of_department || '';
                    document.getElementById('edit-department-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load department: ${err.message}`);
                }
            } else if (action === 'edit-faculty') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/faculties/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const faculty = await response.json();
                    document.getElementById('edit-faculty-id').value = faculty.id || '';
                    document.getElementById('edit-faculty-name').value = faculty.faculty_name || '';
                    document.getElementById('edit-dean').value = faculty.dean || '';
                    document.getElementById('edit-faculty-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load faculty: ${err.message}`);
                }
            } else if (action === 'edit-session') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/attendance-sessions/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const session = await response.json();
                    document.getElementById('edit-session-id').value = session.id || '';
                    document.getElementById('edit-session-name').value = session.session_name || '';
                    document.getElementById('edit-start-date').value = session.start_date || '';
                    document.getElementById('edit-end-date').value = session.end_date || '';
                    document.getElementById('edit-status').value = session.status || '';
                    document.getElementById('edit-session-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load session: ${err.message}`);
                }
            } else if (action === 'edit-attendance') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/attendance-records/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const record = await response.json();
                    document.getElementById('edit-attendance-id').value = record.id || '';
                    document.getElementById('edit-student-id').value = record.student_id || '';
                    document.getElementById('edit-course-id').value = record.course_id || '';
                    document.getElementById('edit-session-id').value = record.session_id || '';
                    document.getElementById('edit-date').value = record.date || '';
                    document.getElementById('edit-status').value = record.status || '';
                    document.getElementById('edit-remarks').value = record.remarks || '';
                    document.getElementById('edit-attendance-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load attendance record: ${err.message}`);
                }
            } else if (action === 'edit-academic-year') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/academic-years/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const year = await response.json();
                    document.getElementById('edit-academic-year-id').value = year.id || '';
                    document.getElementById('edit-name').value = year.name || '';
                    document.getElementById('edit-start-date').value = year.start_date || '';
                    document.getElementById('edit-end-date').value = year.end_date || '';
                    document.getElementById('edit-status').value = year.status || '';
                    document.getElementById('edit-academic-year-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load academic year: ${err.message}`);
                }
            } else if (action === 'edit-administrator') {
                const id = button.getAttribute('data-id');
                try {
                    const response = await fetch(`${API_BASE_URL}/admin/admins/${id}`, {
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const admin = await response.json();
                    document.getElementById('edit-administrator-id').value = admin.id || '';
                    document.getElementById('edit-first-name').value = admin.first_name || '';
                    document.getElementById('edit-last-name').value = admin.last_name || '';
                    document.getElementById('edit-email').value = admin.email || '';
                    document.getElementById('edit-username').value = admin.username || '';
                    document.getElementById('edit-role').value = admin.role || '';
                    document.getElementById('edit-status').value = admin.status || '';
                    document.getElementById('edit-administrator-section')?.classList.remove('hidden');
                } catch (err) {
                    alert(`Failed to load admin: ${err.message}`);
                }
            } else if (action.startsWith('delete-')) {
                currentDeleteId = button.getAttribute('data-id');
                document.getElementById('delete-confirmation-modal')?.classList.remove('hidden');
                ['application', 'status', 'student', 'lecturer', 'course', 'department', 'faculty', 'session', 'attendance', 'notification', 'academic-year', 'administrator'].forEach(entity => {
                    document.getElementById(`delete-${entity}-error`)?.classList.add('hidden');
                    document.getElementById(`delete-${entity}-success`)?.classList.add('hidden');
                });
            }
        });
    });

    // Delete confirmation modal
    const deleteModal = document.getElementById('delete-confirmation-modal');
    const cancelDelete = document.getElementById('cancel-delete');
    const confirmDelete = document.getElementById('confirm-delete');

    if (deleteModal && cancelDelete && confirmDelete) {
        cancelDelete.addEventListener('click', () => {
            deleteModal.classList.add('hidden');
            currentDeleteId = null;
        });

        confirmDelete.addEventListener('click', async () => {
            const pageSections = {
                'applications-section': { error: 'delete-application-error', success: 'delete-application-success', section: 'applications-section', fetch: fetchApplications, entity: 'application', api: 'applications' },
                'statuses-section': { error: 'delete-status-error', success: 'delete-status-success', section: 'statuses-section', fetch: fetchStatuses, entity: 'status', api: 'admission-statuses' },
                'students-section': { error: 'delete-student-error', success: 'delete-student-success', section: 'students-section', fetch: fetchStudents, entity: 'student', api: 'students' },
                'lecturers-section': { error: 'delete-lecturer-error', success: 'delete-lecturer-success', section: 'lecturers-section', fetch: fetchLecturers, entity: 'lecturer', api: 'lecturers' },
                'courses-section': { error: 'delete-course-error', success: 'delete-course-success', section: 'courses-section', fetch: fetchCourses, entity: 'course', api: 'courses' },
                'departments-section': { error: 'delete-department-error', success: 'delete-department-success', section: 'departments-section', fetch: fetchDepartments, entity: 'department', api: 'departments' },
                'faculties-section': { error: 'delete-faculty-error', success: 'delete-faculty-success', section: 'faculties-section', fetch: fetchFaculties, entity: 'faculty', api: 'faculties' },
                'sessions-section': { error: 'delete-session-error', success: 'delete-session-success', section: 'sessions-section', fetch: fetchSessions, entity: 'session', api: 'attendance-sessions' },
                'attendance-records-section': { error: 'delete-attendance-error', success: 'delete-attendance-success', section: 'attendance-records-section', fetch: fetchAttendanceRecords, entity: 'attendance', api: 'attendance-records' },
                'notifications-section': { error: 'delete-notification-error', success: 'delete-notification-success', section: 'notifications-section', fetch: fetchNotifications, entity: 'notification', api: 'notifications' },
                'academic-years-section': { error: 'delete-academic-year-error', success: 'delete-academic-year-success', section: 'academic-years-section', fetch: fetchAcademicYears, entity: 'academic-year', api: 'academic-years' },
                'administrators-section': { error: 'delete-administrator-error', success: 'delete-administrator-success', section: 'administrators-section', fetch: fetchAdmins, entity: 'admin', api: 'admins' }
            };

            let currentPage = null;
            for (const [sectionId, config] of Object.entries(pageSections)) {
                if (document.getElementById(sectionId)) {
                    currentPage = config;
                    break;
                }
            }

            if (!currentPage) return;

            const error = document.getElementById(currentPage.error);
            const success = document.getElementById(currentPage.success);

            error.classList.add('hidden');
            success.classList.add('hidden');

            try {
                const response = await fetch(`${API_BASE_URL}/admin/${currentPage.api}/${currentDeleteId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    if (response.status === 401) throw new Error('Unauthorized: Please log in');
                    if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                    if (response.status === 404) throw new Error(`${currentPage.entity} not found`);
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }

                success.classList.remove('hidden');
                setTimeout(() => {
                    deleteModal.classList.add('hidden');
                    sections.forEach(section => section.classList.add('hidden'));
                    document.getElementById(currentPage.section)?.classList.remove('hidden');
                    currentPage.fetch();
                }, 2000);
            } catch (err) {
                error.classList.remove('hidden');
                error.textContent = `Failed to delete ${currentPage.entity}: ${err.message}`;
            }
        });
    }

    // Form submission handlers
    const forms = [
        { id: 'create-application-form', loading: 'create-application-loading', error: 'create-application-error', success: 'create-application-success', section: 'applications-section', fetch: fetchApplications, entity: 'application', api: 'applications', method: 'POST' },
        { id: 'edit-application-form', loading: 'edit-application-loading', error: 'edit-application-error', success: 'edit-application-success', section: 'applications-section', fetch: fetchApplications, entity: 'application', api: 'admission-applications', method: 'PUT' },
        { id: 'update-status-form', loading: 'update-status-loading', error: 'update-status-error', success: 'update-status-success', section: 'statuses-section', fetch: fetchStatuses, entity: 'status', api: 'admission-statuses', method: 'POST' },
        { id: 'create-student-form', loading: 'create-student-loading', error: 'create-student-error', success: 'create-student-success', section: 'students-section', fetch: fetchStudents, entity: 'student', api: 'students', method: 'POST' },
        { id: 'edit-student-form', loading: 'edit-student-loading', error: 'edit-student-error', success: 'edit-student-success', section: 'students-section', fetch: fetchStudents, entity: 'student', api: 'students', method: 'PUT' },
        { id: 'create-lecturer-form', loading: 'create-lecturer-loading', error: 'create-lecturer-error', success: 'create-lecturer-success', section: 'lecturers-section', fetch: fetchLecturers, entity: 'lecturer', api: 'lecturers', method: 'POST' },
        { id: 'edit-lecturer-form', loading: 'edit-lecturer-loading', error: 'edit-lecturer-error', success: 'edit-lecturer-success', section: 'lecturers-section', fetch: fetchLecturers, entity: 'lecturer', api: 'lecturers', method: 'PUT' },
        { id: 'create-course-form', loading: 'create-course-loading', error: 'create-course-error', success: 'create-course-success', section: 'courses-section', fetch: fetchCourses, entity: 'course', api: 'courses', method: 'POST' },
        { id: 'edit-course-form', loading: 'edit-course-loading', error: 'edit-course-error', success: 'edit-course-success', section: 'courses-section', fetch: fetchCourses, entity: 'course', api: 'courses', method: 'PUT' },
        { id: 'create-department-form', loading: 'create-department-loading', error: 'create-department-error', success: 'create-department-success', section: 'departments-section', fetch: fetchDepartments, entity: 'department', api: 'departments', method: 'POST' },
        { id: 'edit-department-form', loading: 'edit-department-loading', error: 'edit-department-error', success: 'edit-department-success', section: 'departments-section', fetch: fetchDepartments, entity: 'department', api: 'departments', method: 'PUT' },
        { id: 'create-faculty-form', loading: 'create-faculty-loading', error: 'create-faculty-error', success: 'create-faculty-success', section: 'faculties-section', fetch: fetchFaculties, entity: 'faculty', api: 'faculties', method: 'POST' },
        { id: 'edit-faculty-form', loading: 'edit-faculty-loading', error: 'edit-faculty-error', success: 'edit-faculty-success', section: 'faculties-section', fetch: fetchFaculties, entity: 'faculty', api: 'faculties', method: 'POST' },
        { id: 'create-session-form', loading: 'create-session-loading', error: 'create-session-error', success: 'create-session-success', section: 'sessions-section', fetch: fetchSessions, entity: 'session', api: 'attendance-sessions', method: 'POST' },
        { id: 'edit-session-form', loading: 'edit-session-loading', error: 'edit-session-error', success: 'edit-session-success', section: 'sessions-section', fetch: fetchSessions, entity: 'session', api: 'attendance-sessions', method: 'PUT' },
        { id: 'create-attendance-form', loading: 'create-attendance-loading', error: 'create-attendance-error', success: 'create-attendance-success', section: 'attendance-records-section', fetch: fetchAttendanceRecords, entity: 'attendance', api: 'attendance-records', method: 'POST' },
        { id: 'edit-attendance-form', loading: 'edit-attendance-loading', error: 'edit-attendance-error', success: 'edit-attendance-success', section: 'attendance-records-section', fetch: fetchAttendanceRecords, entity: 'attendance', api: 'attendance-records', method: 'PUT' },
        { id: 'create-notification-form', loading: 'create-notification-loading', error: 'create-notification-error', success: 'create-notification-success', section: 'notifications-section', fetch: fetchNotifications, entity: 'notification', api: 'notifications', method: 'POST' },
        { id: 'create-academic-year-form', loading: 'create-academic-year-loading', error: 'create-academic-year-error', success: 'create-academic-year-success', section: 'academic-years-section', fetch: fetchAcademicYears, entity: 'academic-year', api: 'academic-years', method: 'POST' },
        { id: 'edit-academic-year-form', loading: 'edit-academic-year-loading', error: 'edit-academic-year-error', success: 'edit-academic-year-success', section: 'academic-years-section', fetch: fetchAcademicYears, entity: 'academic-year', api: 'academic-years', method: 'PUT' },
        { id: 'create-administrator-form', loading: 'create-administrator-loading', error: 'create-administrator-error', success: 'create-administrator-success', section: 'administrators-section', fetch: fetchAdmins, entity: 'admin', api: 'admins', method: 'POST' },
        { id: 'edit-administrator-form', loading: 'edit-administrator-loading', error: 'edit-administrator-error', success: 'edit-administrator-success', section: 'administrators-section', fetch: fetchAdmins, entity: 'admin', api: 'admins', method: 'PUT' }
    ];

    forms.forEach(form => {
        const formElement = document.getElementById(form.id);
        if (formElement) {
            formElement.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(formElement);
                const data = Object.fromEntries(formData);
                if (form.method === 'PUT' && (form.entity === 'admin' || form.entity === 'student' || form.entity === 'lecturer') && !data.password) {
                    delete data.password;
                }
                const loading = document.getElementById(form.loading);
                const error = document.getElementById(form.error);
                const success = document.getElementById(form.success);

                loading.classList.remove('hidden');
                error.classList.add('hidden');
                success.classList.add('hidden');

                try {
                    const response = await fetch(`${API_BASE_URL}/admin/${form.api}${form.method === 'PUT' ? `/${data[`${form.entity}_id`]}` : ''}`, {
                        method: form.method,
                        body: JSON.stringify(data),
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (!response.ok) {
                        if (response.status === 401) throw new Error('Unauthorized: Please log in');
                        if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                        if (response.status === 400) throw new Error('Bad request: Invalid data');
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }

                    success.classList.remove('hidden');
                    formElement.reset();
                    setTimeout(() => {
                        sections.forEach(section => section.classList.add('hidden'));
                        document.getElementById(form.section).classList.remove('hidden');
                        form.fetch();
                    }, 2000);
                } catch (err) {
                    error.classList.remove('hidden');
                    error.textContent = `Failed to ${form.method === 'POST' ? 'create' : 'update'} ${form.entity}: ${err.message}`;
                } finally {
                    loading.classList.add('hidden');
                }
            });
        }
    });

    // Fetch functions
    async function fetchApplications() {
        const tableBody = document.getElementById('applications-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('applications-loading');
        const error = document.getElementById('applications-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/applications`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const applications = await response.json();
            tableBody.innerHTML = '';
            applications.forEach(app => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${app.id}</td>
                    <td>${app.applicant_name}</td>
                    <td>${app.email}</td>
                    <td>${app.program}</td>
                    <td>${app.status}</td>
                    <td>${app.submission_date}</td>
                    <td>${app.department_id || '-'}</td>
                    <td>
                        <button class="action-button view" data-action="view-application" data-id="${app.id}">View</button>
                        <button class="action-button edit" data-action="edit-application" data-id="${app.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-application" data-id="${app.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load applications: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchStatuses() {
        const tableBody = document.getElementById('statuses-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('statuses-loading');
        const error = document.getElementById('statuses-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/admission-statuses`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const statuses = await response.json();
            tableBody.innerHTML = '';
            statuses.forEach(status => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${status.application_id}</td>
                    <td>${status.applicant_name}</td>
                    <td>${status.status}</td>
                    <td>${status.department_id || '-'}</td>
                    <td>${status.last_updated}</td>
                    <td>
                        <button class="action-button delete" data-action="delete-status" data-id="${status.application_id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load statuses: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchStudents() {
        const tableBody = document.getElementById('students-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('students-loading');
        const error = document.getElementById('students-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/students`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const students = await response.json();
            tableBody.innerHTML = '';
            students.forEach(student => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${student.id}</td>
                    <td>${student.first_name} ${student.last_name}</td>
                    <td>${student.matric_no}</td>
                    <td>${student.level}</td>
                    <td>${student.department_id || '-'}</td>
                    <td>${student.email}</td>
                    <td>
                        <button class="action-button view" data-action="view-student" data-id="${student.id}">View</button>
                        <button class="action-button edit" data-action="edit-student" data-id="${student.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-student" data-id="${student.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load students: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchLecturers() {
        const tableBody = document.getElementById('lecturers-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('lecturers-loading');
        const error = document.getElementById('lecturers-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/lecturers`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const lecturers = await response.json();
            tableBody.innerHTML = '';
            lecturers.forEach(lecturer => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${lecturer.id}</td>
                    <td>${lecturer.first_name} ${lecturer.last_name}</td>
                    <td>${lecturer.staff_id}</td>
                    <td>${lecturer.department_id || '-'}</td>
                    <td>${lecturer.email}</td>
                    <td>
                        <button class="action-button view" data-action="view-lecturer" data-id="${lecturer.id}">View</button>
                        <button class="action-button edit" data-action="edit-lecturer" data-id="${lecturer.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-lecturer" data-id="${lecturer.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load lecturers: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchCourses() {
        const tableBody = document.getElementById('courses-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('courses-loading');
        const error = document.getElementById('courses-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/courses`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const courses = await response.json();
            tableBody.innerHTML = '';
            courses.forEach(course => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${course.id}</td>
                    <td>${course.course_code}</td>
                    <td>${course.course_title}</td>
                    <td>${course.department_id || '-'}</td>
                    <td>${course.credits}</td>
                    <td>${course.level}</td>
                    <td>
                        <button class="action-button view" data-action="view-course" data-id="${course.id}">View</button>
                        <button class="action-button edit" data-action="edit-course" data-id="${course.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-course" data-id="${course.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load courses: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchDepartments() {
        const tableBody = document.getElementById('departments-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('departments-loading');
        const error = document.getElementById('departments-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/departments`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const departments = await response.json();
            tableBody.innerHTML = '';
            departments.forEach(department => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${department.id}</td>
                    <td>${department.department_name}</td>
                    <td>${department.faculty_id || '-'}</td>
                    <td>${department.head_of_department || '-'}</td>
                    <td>
                        <button class="action-button view" data-action="view-department" data-id="${department.id}">View</button>
                        <button class="action-button edit" data-action="edit-department" data-id="${department.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-department" data-id="${department.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load departments: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchFaculties() {
        const tableBody = document.getElementById('faculties-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('faculties-loading');
        const error = document.getElementById('faculties-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/faculties`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const faculties = await response.json();
            tableBody.innerHTML = '';
            faculties.forEach(faculty => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${faculty.id}</td>
                    <td>${faculty.faculty_name}</td>
                    <td>${faculty.dean || '-'}</td>
                    <td>
                        <button class="action-button view" data-action="view-faculty" data-id="${faculty.id}">View</button>
                        <button class="action-button edit" data-action="edit-faculty" data-id="${faculty.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-faculty" data-id="${faculty.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load faculties: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchSessions() {
        const tableBody = document.getElementById('sessions-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('sessions-loading');
        const error = document.getElementById('sessions-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/attendance-sessions`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const sessions = await response.json();
            tableBody.innerHTML = '';
            sessions.forEach(session => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${session.id}</td>
                    <td>${session.session_name}</td>
                    <td>${session.start_date}</td>
                    <td>${session.end_date}</td>
                    <td>${session.status}</td>
                    <td>
                        <button class="action-button view" data-action="view-session" data-id="${session.id}">View</button>
                        <button class="action-button edit" data-action="edit-session" data-id="${session.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-session" data-id="${session.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load sessions: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchAttendanceRecords() {
        const tableBody = document.getElementById('attendance-records-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('attendance-records-loading');
        const error = document.getElementById('attendance-records-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/attendance-records`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const records = await response.json();
            tableBody.innerHTML = '';
            records.forEach(record => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${record.id}</td>
                    <td>${record.student_id || '-'}</td>
                    <td>${record.course_id || '-'}</td>
                    <td>${record.session_id || '-'}</td>
                    <td>${record.date}</td>
                    <td>${record.status}</td>
                    <td>${record.remarks || '-'}</td>
                    <td>
                        <button class="action-button view" data-action="view-attendance" data-id="${record.id}">View</button>
                        <button class="action-button edit" data-action="edit-attendance" data-id="${record.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-attendance" data-id="${record.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load attendance records: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchNotifications() {
        const tableBody = document.getElementById('notifications-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('notifications-loading');
        const error = document.getElementById('notifications-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/notifications`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const notifications = await response.json();
            tableBody.innerHTML = '';
            notifications.forEach(notification => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${notification.id}</td>
                    <td>${notification.title}</td>
                    <td>${notification.message}</td>
                    <td>${notification.created_at}</td>
                    <td>${notification.recipient_type}</td>
                    <td>${notification.status}</td>
                    <td>
                        <button class="action-button delete" data-action="delete-notification" data-id="${notification.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load notifications: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchAcademicYears() {
        const tableBody = document.getElementById('academic-years-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('academic-years-loading');
        const error = document.getElementById('academic-years-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/academic-years`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const academicYears = await response.json();
            tableBody.innerHTML = '';
            academicYears.forEach(year => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${year.id}</td>
                    <td>${year.name}</td>
                    <td>${year.start_date}</td>
                    <td>${year.end_date}</td>
                    <td>${year.status}</td>
                    <td>
                        <button class="action-button view" data-action="view-academic-year" data-id="${year.id}">View</button>
                        <button class="action-button edit" data-action="edit-academic-year" data-id="${year.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-academic-year" data-id="${year.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load academic years: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    async function fetchAdmins() {
        const tableBody = document.getElementById('administrators-table-body');
        if (!tableBody) return;

        const loading = document.getElementById('administrators-loading');
        const error = document.getElementById('administrators-error');

        loading.classList.remove('hidden');
        error.classList.add('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/admin/admins`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                if (response.status === 401) throw new Error('Unauthorized: Please log in');
                if (response.status === 403) throw new Error('Forbidden: Insufficient permissions');
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const admins = await response.json();
            tableBody.innerHTML = '';
            admins.forEach(admin => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${admin.id}</td>
                    <td>${admin.first_name} ${admin.last_name}</td>
                    <td>${admin.email}</td>
                    <td>${admin.username}</td>
                    <td>${admin.role}</td>
                    <td>${admin.status}</td>
                    <td>
                        <button class="action-button view" data-action="view-administrator" data-id="${admin.id}">View</button>
                        <button class="action-button edit" data-action="edit-administrator" data-id="${admin.id}">Edit</button>
                        <button class="action-button delete" data-action="delete-administrator" data-id="${admin.id}">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        } catch (err) {
            error.classList.remove('hidden');
            error.textContent = 'Failed to load admins: ' + err.message;
        } finally {
            loading.classList.add('hidden');
        }
    }

    // Load data based on page
    if (document.getElementById('applications-section')) fetchApplications();
    if (document.getElementById('statuses-section')) fetchStatuses();
    if (document.getElementById('students-section')) fetchStudents();
    if (document.getElementById('lecturers-section')) fetchLecturers();
    if (document.getElementById('courses-section')) fetchCourses();
    if (document.getElementById('departments-section')) fetchDepartments();
    if (document.getElementById('faculties-section')) fetchFaculties();
    if (document.getElementById('sessions-section')) fetchSessions();
    if (document.getElementById('attendance-records-section')) fetchAttendanceRecords();
    if (document.getElementById('notifications-section')) fetchNotifications();
    if (document.getElementById('academic-years-section')) fetchAcademicYears();
    if (document.getElementById('administrators-section')) fetchAdmins();
});