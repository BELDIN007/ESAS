// --- Configuration ---
// Replace with the actual URL where your Flask app is running
// Example: If running locally on port 5000
const BASE_URL = "http://127.0.0.1:5000"; // Standard loopback address
const PROFILE_ENDPOINT = "/student/profile";
const API_URL = `${BASE_URL}${PROFILE_ENDPOINT}`;

// Function to fetch and display student profile
async function fetchStudentProfile() {
    // Get references to HTML elements for messages and content
    const loadingMessage = document.getElementById('loading-message');
    const errorMessage = document.getElementById('error-message');
    const profileDetailsDiv = document.getElementById('profile-details');

    // Initial state: Show loading, hide others
    loadingMessage.style.display = 'block';
    errorMessage.style.display = 'none';
    profileDetailsDiv.style.display = 'none';

    // --- Get Authentication Token ---
    // IMPORTANT: Replace 'yourAuthToken' with the actual key
    // used to store the token after successful login in your frontend.
    // This could be in localStorage, sessionStorage, or a cookie.
    const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2FjY291bnRfaWQiOiJ1c3I1NCIsInJvbGUiOiJzdHVkZW50IiwiZW50aXR5X2lkIjoic3R1MzgifQ.y0pMc_hpJCvKg_0gCcIxrJYsD-EisfzGKpHaaHlbt8s'; // Example: getting token from localStorage

    // Check if a token was found
    if (!token) {
         // If no token is found, display an error and stop
         displayError("User not authenticated. Please log in first.");
         console.error("Authentication token not found in localStorage.");
         loadingMessage.style.display = 'none'; // Hide loading message
         return; // Exit the function
    }

    try {
        // Make the GET request to the API endpoint
        // This includes the Authorization header with the token
        const response = await fetch(API_URL, {
            method: 'GET', // Specify the HTTP method
            headers: {
                // Add the Authorization header with the Bearer token
                'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
            }
            // If your backend also relies on session cookies AND the frontend is on a different origin,
            // you might also need: credentials: 'include'
        });

        // Check if the response status is OK (status code 200-299)
        if (!response.ok) {
            // Handle HTTP errors (like 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error)
            let userMessage = `Failed to load profile (${response.status}).`;
            if (response.status === 401 || response.status === 403) {
                 userMessage = "Access denied. Please log in again or check your permissions.";
            } else if (response.status === 404) {
                 userMessage = "Student profile not found for the authenticated user.";
            } else if (response.status >= 500) {
                 userMessage = "An error occurred on the server.";
            }

            // Attempt to parse specific error message from backend response if available
            try {
                const errorJson = await response.json();
                if (errorJson && errorJson.error) {
                   userMessage = `Error: ${errorJson.error}`;
                }
                console.error('Backend Error Details:', errorJson); // Log backend error details
            } catch (e) {
                // If response body isn't JSON, log the raw text
                const errorText = await response.text();
                console.error('HTTP error fetching profile:', response.status, response.statusText, 'Response Body:', errorText);
            }

            displayError(userMessage); // Display the determined error message to the user
            return; // Exit the function as the request failed
        }

        // Parse the JSON response body from a successful (2xx) response
        const profileData = await response.json();
        console.log("Profile data received:", profileData); // Log the data for debugging

        // Display the fetched data in the HTML elements
        displayProfileData(profileData);

    } catch (error) {
        // Handle network errors (e.g., server not running, connection refused, no internet)
        console.error('Network or parsing error:', error);
        displayError('Could not connect to the server or process the response.');
    } finally {
        // This block always runs after try/catch, useful for cleanup like hiding loading state
        loadingMessage.style.display = 'none'; // Ensure loading message is hidden
    }
}

// Function to populate the HTML elements with the received data
function displayProfileData(data) {
    // Get REFERENCES TO MESSAGE/PROFILE ELEMENTS AGAIN WITHIN THIS FUNCTION'S SCOPE
    // THIS WAS THE FIX FOR THE ReferenceError
    const loadingMessage = document.getElementById('loading-message');
    const errorMessage = document.getElementById('error-message');
    const profileDetailsDiv = document.getElementById('profile-details');


    // Get the display elements by their IDs - these must match IDs in your HTML
    const studentIdSpan = document.getElementById('student-id');
    const firstNameSpan = document.getElementById('first-name');
    const lastNameSpan = document.getElementById('last-name');
    const matriculationNumberSpan = document.getElementById('matriculation-number');
    const levelSpan = document.getElementById('level');
    // Assuming HTML ID is 'intended-program' based on backend key 'intended_program' for clarity
    const programSpan = document.getElementById('intended-program');
    // Assuming HTML ID is 'department-name' based on backend key 'department_name'
    const departmentNameSpan = document.getElementById('department-name');
    const emailSpan = document.getElementById('email');
    const contactNumberSpan = document.getElementById('contact-number');
    const dateOfBirthSpan = document.getElementById('date-of-birth');
    const genderSpan = document.getElementById('gender');


    // Update the text content of each span with the data from the response
    // Use || 'N/A' to display 'N/A' if the data field is missing or null
    // Added checks for element existence before setting textContent
    if (studentIdSpan) studentIdSpan.textContent = data.student_id || 'N/A';
    if (firstNameSpan) firstNameSpan.textContent = data.first_name || 'N/A';
    if (lastNameSpan) lastNameSpan.textContent = data.last_name || 'N/A';
    // FIX: Corrected typo from matriculationSpan to matriculationNumberSpan
    if (matriculationNumberSpan) matriculationNumberSpan.textContent = data.matriculation_number || 'N/A';
    if (levelSpan) levelSpan.textContent = data.level || 'N/A';
    // Use the backend data key 'intended_program' for the element with ID 'intended-program'
    if (programSpan) programSpan.textContent = data.intended_program || 'N/A';
     // Use the backend data key 'department_name' for the element with ID 'department-name'
    if (departmentNameSpan) departmentNameSpan.textContent = data.department_name || 'N/A';
    if (emailSpan) emailSpan.textContent = data.email || 'N/A';
    if (contactNumberSpan) contactNumberSpan.textContent = data.contact_number || 'N/A';
    // Basic handling for potential date objects/strings - might need more robust formatting
    if (dateOfBirthSpan) dateOfBirthSpan.textContent = data.date_of_birth ? new Date(data.date_of_birth).toLocaleDateString() : 'N/A';
    if (genderSpan) genderSpan.textContent = data.gender || 'N/A';


    // Hide loading/error messages and show the profile div
    // Now these variables are defined in this function's scope, so these lines will work
    if (loadingMessage) loadingMessage.style.display = 'none';
    if (errorMessage) errorMessage.style.display = 'none';
    if (profileDetailsDiv) profileDetailsDiv.style.display = 'block'; // Make the profile details visible
}

// --- Event Listener ---
// Call the fetch function when the entire HTML document has been loaded and parsed
document.addEventListener('DOMContentLoaded', fetchStudentProfile);