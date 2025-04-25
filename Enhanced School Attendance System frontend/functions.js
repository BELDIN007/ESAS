// Get references to the menu toggle button, sidebar, and overlay
const menuToggle = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('.sidebar');
const overlay = document.querySelector('.overlay');

// Add event listener to the menu toggle button
// When the button is clicked, toggle the 'open' class on the sidebar
// and the 'visible' class on the overlay.
menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('visible');
});

// Add event listener to the overlay
// When the overlay is clicked, close the sidebar and hide the overlay.
// This provides a way to close the sidebar by clicking outside of it.
overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
});

// Optional: Add event listener to navigation links
// When a navigation link inside the sidebar is clicked, close the sidebar
// and hide the overlay. This is useful for single-page applications
// where clicking a link doesn't cause a full page reload.
const navLinks = document.querySelectorAll('.navigation a');
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const calendarDates = document.querySelector('.calendar-table tbody');
    const calendarHeader = document.querySelector('.calendar-header h2');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');


    let currentDate = new Date();

    function renderCalendar() {
        calendarDates.innerHTML = ''; // Clear previous dates

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth(); // 0-indexed month

        // Get the first day of the month (0 for Sunday, 6 for Saturday)
        const firstDayOfMonth = new Date(year, month, 1).getDay();

        // Get the number of days in the current month
        const lastDayOfMonth = new Date(year, month + 1, 0).getDate();

        // Get the number of days in the previous month to show trailing dates
        const lastDayOfPrevMonth = new Date(year, month, 0).getDate();

        // Update the header with the current month and year
        const monthNames = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"];
        calendarHeader.textContent = `${monthNames[month]} ${year}`;

        let date = 1;
        let nextMonthDate = 1;

        // Create the rows and columns for the calendar
        for (let i = 0; i < 6; i++) { // 6 rows to accommodate all dates
            const row = document.createElement('tr');

            for (let j = 0; j < 7; j++) { // 7 days a week
                const cell = document.createElement('td');

                if (i === 0 && j < firstDayOfMonth) {
                    // Add dates from the previous month
                    const prevMonthDay = lastDayOfPrevMonth - firstDayOfMonth + j + 1;
                    cell.textContent = prevMonthDay;
                    cell.classList.add('inactive');
                } else if (date > lastDayOfMonth) {
                    // Add dates from the next month
                    cell.textContent = nextMonthDate;
                    cell.classList.add('inactive');
                    nextMonthDate++;
                } else {
                    // Add dates for the current month
                    // Wrap the date in a span for better centering with the circular background
                    cell.innerHTML = `<span>${date}</span>`;


                    // Highlight the current day
                    const today = new Date();
                    if (year === today.getFullYear() && month === today.getMonth() && date === today.getDate()) {
                        cell.classList.add('current-day');
                    }

                    date++;
                }
                row.appendChild(cell);
            }
            calendarDates.appendChild(row);

            // Stop creating rows if all dates of the current month have been placed
            // This helps prevent extra empty rows at the end of short months
            if (date > lastDayOfMonth && i > 3) {
                 break;
            }
        }
    }

    // Event Listeners for Navigation Buttons
    prevMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    // Initial render
    renderCalendar();

});