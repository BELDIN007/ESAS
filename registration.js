document.addEventListener('DOMContentLoaded', () => {
    // Get references to the different form sections and links
    const loginForm = document.getElementById('login-form');
    const showRegisterLink = document.getElementById('show-register');
    const registerOptions = document.getElementById('register-options');
    const backToLoginLink = document.getElementById('back-to-login');
    const registerTypeButtons = document.querySelectorAll('.register-type-button');
    const lecturerRegisterForm = document.getElementById('lecturer-register-form');
    const studentRegisterForm = document.getElementById('student-register-form');
    const backToOptionsLecturer = document.getElementById('back-to-options-lecturer');
    const backToOptionsStudent = document.getElementById('back-to-options-student');

    // Function to hide all form sections
    function hideAllFormsAndOptions() {
        loginForm.classList.add('hidden');
        showRegisterLink.classList.add('hidden'); // Hide the initial register link
        registerOptions.classList.add('hidden');
        backToLoginLink.classList.add('hidden'); // Hide the back to login link
        lecturerRegisterForm.classList.add('hidden');
        studentRegisterForm.classList.add('hidden');
        backToOptionsLecturer.classList.add('hidden'); // Hide back link in lecturer form
        backToOptionsStudent.classList.add('hidden'); // Hide back link in student form
    }

    // Function to show the login form
    function showLogin() {
        hideAllFormsAndOptions();
        loginForm.classList.remove('hidden');
        showRegisterLink.classList.remove('hidden');
    }

    // Function to show the register options
    function showRegisterOptions() {
        hideAllFormsAndOptions();
        registerOptions.classList.remove('hidden');
        backToLoginLink.classList.remove('hidden');
    }

    // Function to show the lecturer registration form
    function showLecturerRegister() {
        hideAllFormsAndOptions();
        lecturerRegisterForm.classList.remove('hidden');
        backToOptionsLecturer.classList.remove('hidden');
    }

    // Function to show the student registration form
    function showStudentRegister() {
        hideAllFormsAndOptions();
        studentRegisterForm.classList.remove('hidden');
         backToOptionsStudent.classList.remove('hidden');
    }

    // Add event listeners

    // Click "Register" link to show register options
    showRegisterLink.addEventListener('click', showRegisterOptions);

    // Click "Back to Login" link to show login form
    backToLoginLink.addEventListener('click', showLogin);

    // Click Lecturer or Student buttons to show respective forms
    registerTypeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const type = button.getAttribute('data-type');
            if (type === 'lecturer') {
                showLecturerRegister();
            } else if (type === 'student') {
                showStudentRegister();
            }
        });
    });

    // Click "Back to Options" links in registration forms
    backToOptionsLecturer.addEventListener('click', showRegisterOptions);
    backToOptionsStudent.addEventListener('click', showRegisterOptions);


    // Set the initial state: show the login form
    showLogin();
});

document.addEventListener('DOMContentLoaded', () => {
    // Get references to the different form sections and links
    // (These references are needed for the form switching logic from earlier)
    const loginForm = document.getElementById('login-form');
    const showRegisterLink = document.getElementById('show-register');
    const registerOptions = document.getElementById('register-options');
    const backToLoginLink = document.getElementById('back-to-login');
    const registerTypeButtons = document.querySelectorAll('.register-type-button');

    // Get references specifically for the registration forms
    const lecturerRegisterForm = document.getElementById('lecturer-register-form');
    const studentRegisterForm = document.getElementById('student-register-form');
    const backToOptionsLecturer = document.getElementById('back-to-options-lecturer');
    const backToOptionsStudent = document.getElementById('back-to-options-student');

    // --- Existing Form Switching Logic (Include this if it's not already in your file) ---
    // Function to hide all form sections
    function hideAllFormsAndOptions() {
        // Check if elements exist before trying to add class (important if combining scripts)
        if (loginForm) loginForm.classList.add('hidden');
        if (showRegisterLink) showRegisterLink.classList.add('hidden');
        if (registerOptions) registerOptions.classList.add('hidden');
        if (backToLoginLink) backToLoginLink.classList.add('hidden');
        if (lecturerRegisterForm) lecturerRegisterForm.classList.add('hidden');
        if (studentRegisterForm) studentRegisterForm.classList.add('hidden');
        if (backToOptionsLecturer) backToOptionsLecturer.classList.add('hidden');
        if (backToOptionsStudent) backToOptionsStudent.classList.add('hidden');
         // You might also need to hide the initial login button if it's separate from the form
         const loginButton = document.getElementById('login-button'); // Assuming an ID exists
         if (loginButton) loginButton.classList.add('hidden');
    }

    // Function to show the login form
    function showLogin() {
        hideAllFormsAndOptions();
        if (loginForm) loginForm.classList.remove('hidden');
        if (showRegisterLink) showRegisterLink.classList.remove('hidden');
         // You might also need to show the initial login button
         const loginButton = document.getElementById('login-button');
         if (loginButton) loginButton.classList.remove('hidden');
    }

    // Function to show the register options
    function showRegisterOptions() {
        hideAllFormsAndOptions();
        if (registerOptions) registerOptions.classList.remove('hidden');
        if (backToLoginLink) backToLoginLink.classList.remove('hidden');
    }

    // Function to show the lecturer registration form
    function showLecturerRegister() {
        hideAllFormsAndOptions();
        if (lecturerRegisterForm) lecturerRegisterForm.classList.remove('hidden');
        if (backToOptionsLecturer) backToOptionsLecturer.classList.remove('hidden');
    }

    // Function to show the student registration form
    function showStudentRegister() {
        hideAllFormsAndOptions();
        if (studentRegisterForm) studentRegisterForm.classList.remove('hidden');
        if (backToOptionsStudent) backToOptionsStudent.classList.remove('hidden');
    }

     // Add event listeners for switching sections (Include this if not already present)
     if (showRegisterLink) showRegisterLink.addEventListener('click', showRegisterOptions);
     if (backToLoginLink) backToLoginLink.addEventListener('click', showLogin);

     if (registerTypeButtons) {
        registerTypeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const type = button.getAttribute('data-type');
                if (type === 'lecturer') {
                    showLecturerRegister();
                } else if (type === 'student') {
                    showStudentRegister();
                }
            });
        });
     }

     if (backToOptionsLecturer) backToOptionsLecturer.addEventListener('click', showRegisterOptions);
     if (backToOptionsStudent) backToOptionsStudent.addEventListener('click', showRegisterOptions);

    // --- End of Existing Form Switching Logic ---


    // --- New Form Submission Logic ---

    // Function to handle form submission
    async function handleRegistrationSubmit(event) {
        event.preventDefault(); // Prevent default form submission (page reload)

        const form = event.target;
        const formId = form.id;
        let url = '';
        const formData = {};

        // Collect data from form inputs based on their 'name' attributes
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
             // Only include elements with a name attribute and are not disabled
             if (input.name && !input.disabled) {
                 // Special handling for date to ensure format matches backend expectation if needed
                 if (input.type === 'date' && input.value) {
                      // You might need to reformat date here depending on backend preference
                      // For now, sending YYYY-MM-DD which is default input[type="date"] format
                       formData[input.name] = input.value;
                 } else {
                    formData[input.name] = input.value;
                 }
             }
        });

        // --- Client-side Validation ---x

        // Password Confirmation Check
        if (formData.proposed_password !== formData.confirm_password) {
            alert('Error: Passwords do not match!');
            return; // Stop submission
        }

        // Basic check for required fields not caught by browser (optional if using 'required')
        // You can add more specific validation here (e.g., email format, phone number format)
        // For example: if (!formData.email || !/\S+@\S+\.\S+/.test(formData.email)) { alert('Invalid email'); return; }


        // Remove the confirm_password field as the backend doesn't expect it
        delete formData.confirm_password;

        // --- Determine Target URL ---

        if (formId === 'student-register-form') {
            url = 'http://127.0.0.1:5000/register/student'; // Match your Flask route
        } else if (formId === 'lecturer-register-form') {
            url = 'http://127.0.0.1:5000/register/lecturer'; // Match your Flask route
            // The backend sets 'level' to 'Lecturer Applicant', so we don't send it from the form.
            // date_of_birth and gender are included if the user entered them (as they have name attributes).
        } else {
            console.error('Unknown form submitted:', formId);
            alert('An internal error occurred. Please try again.');
            return; // Stop submission
        }

        // --- Send Data as JSON ---

        // Optional: Show a loading indicator here
        // Example: const submitButton = form.querySelector('button[type="submit"]');
        // submitButton.disabled = true;
        // submitButton.textContent = 'Submitting...';


        try {
            // Use the Fetch API to send the data
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json' // Tell the server we are sending JSON
                    // Add CSRF token header if your Flask app requires it
                    // 'X-CSRFToken': 'your-csrf-token'
                },
                body: JSON.stringify(formData) // Convert the JavaScript object to a JSON string
            });

            // Parse the JSON response from the backend
            const result = await response.json();

            // --- Handle Response ---

            if (response.ok) { // Check if the status code is 2xx (Success)
                alert(result.message); // Show the success message from the backend

                // Optional: Reset the form or navigate the user
                 form.reset(); // Clear the form fields
                 // showLogin(); // Uncomment to go back to login after successful registration

            } else { // Handle error responses (e.g., 400, 500)
                 // Check if the response contains a specific error message
                alert(`Error: ${result.error || response.statusText || 'Registration failed.'}`); // Show backend error message or status text
            }

        } catch (error) {
            // Handle network errors or errors during fetch/parsing
            console.error('Registration failed:', error);
            alert('An error occurred during registration. Please check your connection and try again.');
        } finally {
             // Optional: Hide loading indicator and re-enable button
             // if (submitButton) {
             //     submitButton.disabled = false;
             //     submitButton.textContent = formId === 'student-register-form' ? 'Submit Student Application' : 'Submit Lecturer Application';
             // }
        }
    }

    // Add submit event listeners to the registration forms
    // Ensure the forms exist in the HTML before adding listeners
    if (lecturerRegisterForm) {
        lecturerRegisterForm.addEventListener('submit', handleRegistrationSubmit);
    }
     if (studentRegisterForm) {
        studentRegisterForm.addEventListener('submit', handleRegistrationSubmit);
    }


    // --- Initial State (Include this if not already present) ---
    // Set the initial state: show the login form
    showLogin();
});