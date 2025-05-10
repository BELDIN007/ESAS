// --- Configuration ---
// Replace with the actual URL where your Flask app is running
// Example: If running locally on port 5000
const BASE_URL = "https://esas.onrender.com"; // Standard loopback address

const PROFILE_ENDPOINT = "/student/profile";
const NOTIFICATIONS_ENDPOINT = "/student/notifications"; // Endpoint for notifications

const PROFILE_API_URL = `${BASE_URL}${PROFILE_ENDPOINT}`;
const NOTIFICATIONS_API_URL = `${BASE_URL}${NOTIFICATIONS_ENDPOINT}`;

// --- Hardcoded Token for Testing (Replace with dynamic retrieval in production) ---
// Make sure this token is valid and not expired on your backend
const TEST_AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2FjY291bnRfaWQiOiJ1c3I1NCIsInJvbGUiOiJzdHVkZW50IiwiZW50aXR5X2lkIjoic3R1MzgifQ.y0pMc_hpJCvKg_0gCcIxrJYsD-EisfzGKpHaaHlbt8s';


// --- Function to display an error message ---
// This function can target different error message elements by ID
function displayError(message, targetElementId) {
    const errorMessageElement = document.getElementById(targetElementId);
    // Infer the corresponding loading element ID (e.g., 'error-message' -> 'loading-message')
    const loadingMessageElement = document.getElementById(targetElementId.replace('error', 'loading'));

    // Hide the corresponding loading message
    if (loadingMessageElement) loadingMessageElement.style.display = 'none';

    // If the target error element exists, set its text and display it
    if (errorMessageElement) {
        errorMessageElement.textContent = message;
        errorMessageElement.style.display = 'block';
    } else {
        // If the element wasn't found, log the error to the console
        console.error(`Error element with ID "${targetElementId}" not found, displaying in console:`, message);
    }

    // Additionally, hide the main profile and notifications content divs on error
    // (Assuming these exist in your HTML)
    const profileDetailsDiv = document.getElementById('profile-details');
    const notificationsListElement = document.getElementById('notifications-list');
    const qrcodeDiv = document.getElementById('qrcode'); // Also clear QR div on error

    if (profileDetailsDiv) profileDetailsDiv.style.display = 'none';
    if (notificationsListElement) notificationsListElement.innerHTML = ''; // Clear list
     if (qrcodeDiv) qrcodeDiv.innerHTML = ''; // Clear QR code
}


// --- Function to fetch and display student profile and QR code ---
async function fetchStudentProfile() {
    // Get references to HTML elements for messages, content, and QR code
    const loadingMessage = document.getElementById('loading-message');
    const errorMessage = document.getElementById('error-message');
    const profileDetailsDiv = document.getElementById('profile-details');
    const qrcodeDiv = document.getElementById('qrcode'); // Get the QR code container div
    const qrCodeDataSpan = document.getElementById('qr-code-data'); // Raw QR data span


    // Initial state: Show loading, hide others
    if (loadingMessage) loadingMessage.style.display = 'block';
    if (errorMessage) errorMessage.style.display = 'none';
    if (profileDetailsDiv) profileDetailsDiv.style.display = 'none';
    if (qrcodeDiv) qrcodeDiv.innerHTML = ''; // Clear any previous QR code content
    if (qrCodeDataSpan) qrCodeDataSpan.style.display = 'none'; // Hide raw data span initially


    // --- Get Authentication Token (Using hardcoded token for testing) ---
    const token = TEST_AUTH_TOKEN; // Use the hardcoded test token


    // Check if a token was found (or if the hardcoded placeholder is still there)
    if (!token || token === 'YOUR_APPROVED_STUDENT_JWT_HERE') { // Added check for placeholder
         // If no token is found, display an error and stop
         displayError("Authentication token is missing or not configured. Please log in first.", 'error-message');
         console.error("Authentication token not found or is placeholder.");
         // displayError handles hiding loadingMessage
         return; // Exit the function
    }

    try {
        // Make the GET request to the Profile API endpoint
        const response = await fetch(PROFILE_API_URL, {
            method: 'GET', // Specify the HTTP method
            headers: {
                // Add the Authorization header with the Bearer token
                'Authorization': `Bearer ${token}`,
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
                console.error('Backend Profile Error Details:', errorJson); // Log backend error details
            } catch (e) {
                // If response body isn't JSON, log the raw text
                const errorText = await response.text();
                console.error('HTTP error fetching profile:', response.status, response.statusText, 'Response Body:', errorText);
            }

            displayError(userMessage, 'error-message'); // Display the determined error message to the user
            return; // Exit the function as the request failed
        }

        // Parse the JSON response body from a successful (2xx) response
        const profileData = await response.json();
        console.log("Profile data received:", profileData); // Log the data for debugging - CHECK YOUR CONSOLE FOR THIS!

        // Display the fetched profile data in the HTML elements
        displayProfileData(profileData); // Display the profile details

        // --- Handle QR Code Generation ---
        const qrData = profileData.qr_code_data; // Get the QR data string from the response

        if (!qrData) {
            // If QR data is missing, display a message
            console.warn('QR code data is missing from the backend response.');
             // Optionally display an error message in the profile section if QR is critical
             // displayError('QR code data not found for this student. Ensure the application was approved.', 'error-message');
            // Don't necessarily return here if profile data was fetched successfully
        } else {
            // Check if the QR code library is loaded and the container div exists
            if (typeof QRCode !== 'undefined' && qrcodeDiv) {
                try {
                    // Clear previous QR code content before generating
                    qrcodeDiv.innerHTML = '';

                    // Generate and display the QR code in the qrcodeDiv
                    new QRCode(qrcodeDiv, {
                        text: qrData, // The data to encode in the QR code (the formatted string)
                        width: 200,
                        height: 200,
                        colorDark : "#000000",
                        colorLight : "#ffffff",
                        correctLevel : QRCode.CorrectLevel.H
                    });
                     // Optionally, hide the raw QR data span if you are displaying the image
                     if(qrCodeDataSpan) qrCodeDataSpan.style.display = 'none';

                } catch (e) {
                     console.error('Error generating QR Code:', e);
                     // Display error message in the profile section if QR generation fails
                     displayError('Could not generate QR code image.', 'error-message');
                     // Fallback: display raw QR data if generation fails
                     if(qrCodeDataSpan) {
                         qrCodeDataSpan.textContent = `QR Data: ${qrData}`;
                         qrCodeDataSpan.style.display = 'block';
                     }
                }
            } else {
                // Handle case where QR library is not loaded or qrcodeDiv is missing
                let qrErrorMsg = 'QR code generation failed: ';
                if (typeof QRCode === 'undefined') qrErrorMsg += 'QR code library (qrcode.js) not loaded. ';
                if (!qrcodeDiv) qrErrorMsg += 'HTML element with ID "qrcode" not found. ';
                console.error(qrErrorMsg);
                 // Display error message in the profile section
                displayError('Could not generate QR code image. Check console for details.', 'error-message');

                 // Fallback: display raw QR data if generation fails
                 if(qrCodeDataSpan) {
                     qrCodeDataSpan.textContent = `QR Data: ${qrData}`;
                     qrCodeDataSpan.style.display = 'block';
                 }
            }
        }


    } catch (error) {
        // Handle network errors (e.g., server not running, connection refused, no internet)
        console.error('Network or parsing error fetching profile:', error);
        displayError('Could not connect to the server or process the profile.', 'error-message');
    } finally {
        // Ensure profile loading message is hidden
         const loadingMessage = document.getElementById('loading-message');
         if (loadingMessage && loadingMessage.style.display !== 'none') {
             loadingMessage.style.display = 'none';
         }
         // Note: displayProfileData will handle showing profileDetailsDiv on success
    }
}

// Function to populate the HTML elements with the received profile data
// This function focuses only on displaying the profile details, not the QR code
function displayProfileData(data) {
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
    const admissionDateSpan = document.getElementById('admission-date');
    // qrCodeDataSpan is handled in fetchStudentProfile now


    // Update the text content of each span with the data from the response
    // Use || 'N/A' to display 'N/A' if the data field is missing or null
    // Added checks for element existence before setting textContent
    if (studentIdSpan) studentIdSpan.textContent = data.student_id || 'N/A';
    if (firstNameSpan) firstNameSpan.textContent = data.first_name || 'N/A';
    if (lastNameSpan) lastNameSpan.textContent = data.last_name || 'N/A';
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
    if (admissionDateSpan) admissionDateSpan.textContent = data.admission_date ? new Date(data.admission_date).toLocaleDateString() : 'N/A';
    // Removed display of raw QR code data here

    // Show the profile details div now that data is populated
    const profileDetailsDiv = document.getElementById('profile-details');
    if (profileDetailsDiv) profileDetailsDiv.style.display = 'block';
}


// --- Function to fetch student notifications ---
async function fetchStudentNotifications() {
    // Get references to HTML elements for messages and the notifications list
    const loadingElement = document.getElementById('notifications-loading');
    const errorElement = document.getElementById('notifications-error');
    const notificationsListElement = document.getElementById('notifications-list');

    // Initial state: Show loading, hide error and list
    if (loadingElement) loadingElement.style.display = 'block';
    if (errorElement) errorElement.style.display = 'none';
    if (notificationsListElement) notificationsListElement.innerHTML = ''; // Clear previous list content


    // --- Get Authentication Token (Using hardcoded token for testing) ---
    const token = TEST_AUTH_TOKEN; // Use the hardcoded test token


    // Check if a token was found
    if (!token || token === 'YOUR_APPROVED_STUDENT_JWT_HERE') { // Added check for placeholder
         // If no token is found, display an error and stop
         displayError("Authentication token is missing or not configured. Cannot fetch notifications.", 'notifications-error');
         console.error("Authentication token not found or is placeholder.");
         // displayError handles hiding loadingElement
         return; // Exit the function
    }

    try {
        // Make the GET request to the Notifications API endpoint
        const response = await fetch(NOTIFICATIONS_API_URL, {
            method: 'GET', // Specify the HTTP method
            headers: {
                // Add the Authorization header with the Bearer token
                'Authorization': `Bearer ${token}`,
            }
            // If your backend also relies on session cookies AND the frontend is on a different origin,
            // you might also need: credentials: 'include'
        });

        // Check if the response status is OK (status code 200-299)
        if (!response.ok) {
            // Handle HTTP errors (like 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error)
            let userMessage = `Failed to load notifications (${response.status}).`;
            if (response.status === 401 || response.status === 403) {
                 userMessage = "Access denied. Please log in again or check your permissions.";
            } else if (response.status === 404) {
                 userMessage = "Notifications endpoint not found or no notifications available.";
            } else if (response.status >= 500) {
                 userMessage = "An error occurred on the server while fetching notifications.";
            }

            // Attempt to parse specific error message from backend response if available
            try {
                const errorJson = await response.json();
                if (errorJson && errorJson.error) {
                   userMessage = `Error: ${errorJson.error}`;
                }
                console.error('Backend Notifications Error Details:', errorJson); // Log backend error details
            } catch (e) {
                // If response body isn't JSON, log the raw text
                const errorText = await response.text();
                console.error('HTTP error fetching notifications:', response.status, response.statusText, 'Response Body:', errorText);
            }

            displayError(userMessage, 'notifications-error'); // Display the determined error message
            return; // Exit the function as the request failed
        }

        // Parse the JSON response body from a successful (2xx) response
        const notificationsData = await response.json();
        console.log("Notifications data received:", notificationsData); // Log the data for debugging

        // Display the fetched notifications in the HTML list
        displayNotifications(notificationsData);

    } catch (error) {
        // Handle network errors (e.g., server not running, connection refused, no internet)
        console.error('Network or parsing error fetching notifications:', error);
        displayError('Could not connect to the server or process notifications.', 'notifications-error');
    } finally {
        // Ensure loading message is hidden regardless of outcome
         const loadingElement = document.getElementById('notifications-loading');
         if (loadingElement && loadingElement.style.display !== 'none') {
             loadingElement.style.display = 'none';
         }
         // Note: displayNotifications will handle showing/hiding the list based on data
    }
}

// --- Function to display the list of notifications ---
function displayNotifications(notifications) {
    const notificationsListElement = document.getElementById('notifications-list');
    const loadingElement = document.getElementById('notifications-loading');
    const errorElement = document.getElementById('notifications-error');

    // Hide loading and error messages
    if (loadingElement) loadingElement.style.display = 'none';
    if (errorElement) errorElement.style.display = 'none';

    if (!notificationsListElement) {
        console.error("HTML element with ID 'notifications-list' not found.");
        return; // Cannot display if the list element doesn't exist
    }

    // Clear the current list content
    notificationsListElement.innerHTML = '';

    // Check if there are any notifications
    if (!notifications || notifications.length === 0) {
        // Display a message if no notifications are found
        const noNotificationsItem = document.createElement('li');
        noNotificationsItem.textContent = 'No notifications found.';
        noNotificationsItem.style.textAlign = 'center';
        noNotificationsItem.style.padding = '15px';
        noNotificationsItem.style.color = '#777';
        notificationsListElement.appendChild(noNotificationsItem);
        return; // Stop here if no notifications
    }

    // Loop through the notifications array and create list items
    notifications.forEach(notification => {
        const listItem = document.createElement('li');
        listItem.classList.add('notification-item'); // Use a class for styling

        // Create the inner structure based on your desired layout
        // Use the keys from your backend response
        listItem.innerHTML = `
            <div class="notification-details">
                <p class="notification-title">${notification.title || 'No Title'}</p>
                <p class="notification-message">${notification.message || 'No message content.'}</p>
                <p class="notification-meta">
                    <span>Created:</span> ${notification.created_at ? new Date(notification.created_at).toLocaleString() : 'N/A'}
                    <span>by:</span> ${notification.creator_username || 'Unknown'} (${notification.creator_role || 'N/A'})
                </p>
                <p class="notification-targets">
                    <span>Target:</span> ${notification.target_role || 'N/A'}
                    ${notification.target_department_name ? `<span>Dept:</span> ${notification.target_department_name}` : ''}
                    ${notification.target_course_code ? `<span>Course:</span> ${notification.target_course_code} - ${notification.target_course_title || 'N/A'}` : ''}
                </p>
            </div>
            <div class="notification-info">
                 <p class="notification-type">${notification.target_role || 'General'}</p>
            </div>
        `;

        // Append the created list item to the UL
        notificationsListElement.appendChild(listItem);
    });
}

// --- Event Listener ---
// Call both fetch functions when the entire HTML document has been loaded and parsed
document.addEventListener('DOMContentLoaded', () => {
    fetchStudentProfile(); // Call the profile and QR fetch function
    fetchStudentNotifications(); // Call the notifications fetch function
});

 // Get the button and the notification box elements
 const toggleNotificationBtn = document.getElementById('toggleNotificationBtn');
 const notificationBox = document.getElementById('myNotification');

 // Add event listener to the button to toggle the notification
 toggleNotificationBtn.addEventListener('click', () => {
     // Check if the box currently has the 'show' class
     const isShowing = notificationBox.classList.contains('show');

     if (isShowing) {
         // If it's showing, start the hiding animation
         notificationBox.classList.remove('show');
         // Wait for the transition to finish before setting display to none
         notificationBox.addEventListener('transitionend', function handler() {
             notificationBox.style.display = 'none';
             notificationBox.removeEventListener('transitionend', handler); // Remove listener after it runs
         });
     } else {
         // If it's hidden, set display to block immediately and then add 'show' class
         notificationBox.style.display = 'block';
         // Use a small timeout to allow display:block to take effect before starting transition
         setTimeout(() => {
              notificationBox.classList.add('show');
         }, 10); // A small delay, like 10ms, is often sufficient
     }
 });

 // Add event listener to the notification box to hide it when clicked
 // This listener remains the same as before
 notificationBox.addEventListener('click', () => {
      // Check if the box currently has the 'show' class
     const isShowing = notificationBox.classList.contains('show');
     if (isShowing) {
          // If it's showing, start the hiding animation
         notificationBox.classList.remove('show');
         // Wait for the transition to finish before setting display to none
         notificationBox.addEventListener('transitionend', function handler() {
             notificationBox.style.display = 'none';
             notificationBox.removeEventListener('transitionend', handler); // Remove listener after it runs
         });
     }
 });
