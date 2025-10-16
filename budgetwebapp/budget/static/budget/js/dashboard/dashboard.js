/**
 * dashboard.js
 * JS specifically for the Dashboard page.
 * Handles chart behavior, UI toggles, and modal-triggering animation.
 */

// Toggle row filters visibility
function toggleRowFilters() {
  const checkbox = document.getElementById('filterToggle');
  const filterRows = document.querySelectorAll('.filter-row-wrapper');

  filterRows.forEach(row => {
    if (checkbox.checked) {
      row.classList.add('visible');
    } else {
      row.classList.remove('visible');
    }
  });
}


// This variable will hold a reference to the icon inside the button that was clicked.
// It helps us know *which* drilldown icon should get the rotate effect when the modal opens.
let currentIcon = null;

// Set up a global click event listener on the document.
// This is event delegation — it will catch any click on an element with the `.drilldown-button` class,
// even if the element was added dynamically later (e.g., by HTMX).
document.addEventListener('click', function (e) {
  // Check if the clicked element or one of its parents is a `.drilldown-button`
  const button = e.target.closest('.drilldown-button');
  if (button) {
    // If so, find the `.drilldown-icon` *inside that specific button* and store it
    currentIcon = button.querySelector('.drilldown-icon');
  }
});

// Get a reference to the modal that will show the transaction details
const modal = document.getElementById('modal-transactions-by-cat');

// When the modal is about to be shown (Bootstrap fires `show.bs.modal`):
modal.addEventListener('show.bs.modal', () => {
  // If we have stored a reference to the icon that triggered the modal,
  // add the `rotate` class to visually rotate it (e.g., arrow pointing up)
  if (currentIcon) {
    currentIcon.classList.add('rotate');
  }
});

// When the modal is about to be hidden (Bootstrap fires `hide.bs.modal`):
modal.addEventListener('hide.bs.modal', () => {
  // Remove the `rotate` class to reset the icon's rotation
  if (currentIcon) {
    currentIcon.classList.remove('rotate');
    // Clear the stored icon reference so it doesn't affect future clicks
    currentIcon = null;
  }
});
