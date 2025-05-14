document.addEventListener('DOMContentLoaded', () => {
    // Get a reference to the login form
    const loginForm = document.getElementById('login-form');

    // Check if the login form exists on the page
    if (loginForm) {
        // Add an event listener for the form's submit event
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent the default browser form submission (which would cause a page reload)

            // Get the values from the input fields
            // Make sure your HTML input fields have 'name="username"' and 'name="password"'
            const usernameOrEmailInput = event.target.elements.username; // Get input element by name="username"
            const passwordInput = event.target.elements.password;       // Get input element by name="password"

            const usernameOrEmail = usernameOrEmailInput.value;
            const password = passwordInput.value;

            // Basic client-side validation (optional, but good practice)
            if (!usernameOrEmail || !password) {
                alert('Please enter both username/email and password.');
                return; // Stop the function if fields are empty
            }

            // Prepare the data to send to your backend
            const loginData = {
                // Use the key names that your backend expects (e.g., 'username', 'email', 'password')
                username: usernameOrEmail, // Assuming your backend accepts 'username' or 'email here
                password: password
            };

            // Define the URL for your backend login endpoint on Render
            // *** IMPORTANT: Replace this placeholder URL with your actual Render backend URL ***
            const loginUrl = 'https://esas.onrender.com/login'; // Example: 'https://my-awesome-app.onrender.com/login'

            // Optional: Show a loading indicator or disable the submit button
            const submitButton = loginForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Logging in...';
            }

            try {
                // Use the Fetch API to send the login data to the backend
                const response = await fetch(loginUrl, {
                    method: 'POST', // Use the POST method for sending login credentials
                    headers: {
                        'Content-Type': 'application/json' // Indicate that the request body is JSON
                        // Add any other headers your backend might require (e.g., CSRF token)
                        // 'X-CSRFToken': 'your-csrf-token-here'
                    },
                    body: JSON.stringify(loginData) // Convert the JavaScript object to a JSON string
                });

                // Parse the JSON response from the backend
                const result = await response.json();

                // --- Handle the Backend Response ---

                if (response.ok) { // Check if the HTTP status code is in the 200-299 range (Success)
                    alert(result.message || 'Login successful!'); // Show a success message (use backend message if available)

                    // *** IMPORTANT: Handle successful login based on your backend's response ***
                    // Your backend should ideally send back a token (like JWT) or confirm session creation.
                    // You need to store this token/session ID securely for future authenticated requests.
                    // Example (storing a token in localStorage - be mindful of security for sensitive data):
                    // Check if the backend response contains a 'token' field
                    if (result.token) {
                         // Store the token in localStorage under the key 'authToken'
                         localStorage.setItem('authToken', result.token);
                         console.log('Token stored in localStorage:', result.token); // Optional: for debugging
                    } else {
                         console.warn('Login successful, but no token received from backend.');
                         // Handle this case - perhaps the backend should always send a token on success
                         // You might want to show an error or prevent redirection if no token is received
                         alert('Login successful, but failed to receive authentication token.');
                         // Maybe don't redirect if no token? Or redirect to a page explaining the issue?
                         // For now, we'll still redirect, but log the warning.
                    }


                    // Redirect the user to the next page (e.g., dashboard, home page)
                    // *** IMPORTANT: Replace 'dashboard.html' with the actual URL of your next page ***
                    window.location.href = 'https://beldin007.github.io/ESAS/Student_home.html'; // Example: 'https://my-awesome-app.onrender.com/dashboard'

                } else { // Handle error responses (e.g., 401 Unauthorized, 400 Bad Request, 500 Internal Server Error)
                    // Show an error message to the user
                    // Use the backend's error message if provided, otherwise a generic one
                    alert(`Login failed: ${result.error || response.statusText || 'Invalid credentials.'}`);

                    // Optional: Clear the password field after a failed attempt
                    passwordInput.value = '';
                }

            } catch (error) {
                // Handle network errors (e.g., server is down, no internet connection)
                console.error('Login failed:', error);
                alert('An error occurred during login. Please check your connection and try again.');
            } finally {
                // Optional: Hide loading indicator and re-enable the submit button
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Login'; // Restore original button text
                }
            }
        });
    } else {
        console.error('Login form not found! Make sure an element with id="login-form" exists.');
    }
});
