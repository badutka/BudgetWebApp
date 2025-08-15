/**
 * Prevents clicks on buttons/links inside table cells from triggering row-level events.
 * Re-applies after HTMX swaps in case new rows are injected.
 */
function preventRowClickFromButtons() {
  document.querySelectorAll("td a, td button, .dashboard-card .refresh-button").forEach(el => {
    el.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevents the <tr> click from firing
    });
  });
}

/**
 * Modal configuration for flexible, per-modal behavior.r
 * Each modal has:
 * - `dialogId`: the inner element where HTMX content is swapped
 * - `onShow` (optional): function to run when the modal is shown
 */
const modalConfigs = {
  'modal-transactions-by-cat': {
    dialogId: 'dialog-transactions-by-cat',
    onShow: () => renderChartInModal()
  },
  'modal': {
    dialogId: 'dialog'
    // No special behavior needed
  },
  'dashboard-card-modal': {
    dialogId: 'dialog-dashboard-card-modal'
    // No special behavior needed
  }
};

/**
 * Initialize all modals defined in `modalConfigs`.
 * - Shows modal after HTMX swap
 * - Hides and clears modal content on dismiss or error
 * - Runs optional per-modal behavior (e.g., rendering a chart)
 */
function initModals() {
  Object.entries(modalConfigs).forEach(([modalId, config]) => {
    const modalElement = document.getElementById(modalId);
    if (!modalElement) return;

    const modal = new bootstrap.Modal(modalElement);
    const dialogId = config.dialogId;

    // Show modal after successful HTMX content swap
    htmx.on("htmx:afterSwap", (e) => {
      if (e.detail.target.id === dialogId) {
        modal.show();
        config.onShow?.(); // Run modal-specific logic if provided
      }
    });

    // Hide modal and reload page on HTMX error or server returning empty
    htmx.on("htmx:beforeSwap", (e) => {
      if (e.detail.target.id === dialogId && !e.detail.xhr.response) {
        modal.hide();
        document.location.reload(); // Fallback to full reload on error
        e.detail.shouldSwap = false;
      }
    });

    // Clear modal contents when it’s hidden
    modalElement.addEventListener("hidden.bs.modal", () => {
      const dialog = document.getElementById(dialogId);
      if (dialog) dialog.innerHTML = "";
    });
  });
}

/**
 * Updates the aggregation dropdown button text to reflect
 * the currently selected radio button value.
 *
 * @param {string} fieldName - The `name` attribute of the aggregation radio inputs.
 * @param {boolean} [fullName=false] - If true, display the full capitalized value (e.g., "Month").
 *                                     If false, display just the first letter (e.g., "M").
 *
 * Behavior:
 * - Finds the checked radio button for the given field.
 * - Updates the matching dropdown button's text to show the selection.
 * - Does nothing if no radio is selected or if the button isn't found.
 */
function updateAggregationButtonText(fieldName, fullName = false) {
  const selected = document.querySelector(`input[name="${fieldName}"]:checked`);
  const button = document.getElementById(`${fieldName}DropdownButton`);

  if (selected && button) {
    const value = selected.value;
    const displayValue = fullName
      ? value.charAt(0).toUpperCase() + value.slice(1) // Example: "month" → "Month"
      : value.charAt(0).toUpperCase();                  // Example: "month" → "M"

    button.textContent = `Aggregation (${displayValue})`;
  }
}

/**
 * Initializes the aggregation dropdown:
 * - Ensures a default radio is selected only if none is already checked (server-rendered selection wins).
 * - Updates the dropdown button text to match the selected option.
 * - Attaches change event listeners to radios to update the button text when the selection changes.
 * - Can be safely re-run after HTMX swaps or on page load.
 *
 * @param {string} fieldName - The `name` attribute of the aggregation radio inputs.
 * @param {string} [defaultValue="month"] - The value of the radio to select by default if none are checked.
 * @param {boolean} [fullName=false] - If true, use full names in button text; if false, just first letters.
 *
 * Safety features:
 * - Will not override a selection if one is already checked (avoids "month" overriding "year" after refresh).
 * - Uses a data attribute (`data-agg-init`) to prevent binding duplicate event listeners on the same radio.
 *
 * Usage:
 * - Call once on `DOMContentLoaded` for initial page load.
 * - Call again after any HTMX content swap that re-renders the aggregation dropdown.
 */
function initAggregationDropdown(fieldName, defaultValue = "month", fullName = false) {
  const radios = document.querySelectorAll(`input[name="${fieldName}"]`);
  if (!radios.length) return; // Nothing to do if no radios found

  // 1 If nothing is checked, set the default option
  const alreadyChecked = Array.from(radios).some(r => r.checked);
  if (!alreadyChecked) {
    const def = document.getElementById(`${fieldName}-${defaultValue}`);
    if (def) def.checked = true;
  }

  // 2 Always update the button text to reflect the current selection
  updateAggregationButtonText(fieldName, fullName);

  // 3 Attach change listeners (once per element) to update text when selection changes
  radios.forEach(radio => {
    if (!radio.dataset.aggInit) {
      radio.dataset.aggInit = "1"; // Mark as initialized to avoid duplicate listeners
      radio.addEventListener('change', () => updateAggregationButtonText(fieldName, fullName));
    }
  });
}

function updateDropdownCountBadge(filterName) {
  const checkboxes = document.querySelectorAll(`.form-check-input[name="${filterName}"]`);
  const badge = document.getElementById(`${filterName}-count`);
  if (!badge) return;  // <--- exit if badge not found

  const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

  if (checkedCount > 0) {
    badge.style.display = 'inline-block';
    badge.textContent = checkedCount;
  } else {
    badge.style.display = 'none';
  }
}
/**
 * Update the dropdown button text based on how many checkboxes are selected
 * Used for category filters and parent_category filters
 */
function updateDropdownText(filterName, keepText = false) {
  const checkboxes = document.querySelectorAll(`.form-check-input[name="${filterName}"]`);
  const dropdownButton = document.getElementById(`${filterName}DropdownButton`);
  if (!dropdownButton) return;

  const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

  if (keepText) {
    // Keep original text and add the count in parentheses
    const originalText = dropdownButton.getAttribute('data-original-text') || dropdownButton.textContent;
    dropdownButton.setAttribute('data-original-text', originalText);
//    dropdownButton.textContent = `${originalText} (${checkedCount})`;
    dropdownButton.textContent = `${originalText} (${checkedCount})`;
    dropdownButton.innerHTML = `${originalText} <strong>(${checkedCount})</strong>`;
  } else {
    // Default behavior: "X selected"
    dropdownButton.textContent = `${checkedCount} selected`;
  }
}

/**
 * Set up filter dropdown with 'Select All' functionality and label updating
 */
function setupFilterSelectAll(filterName, keepText = false) {
  const selectAllCheckbox = document.getElementById(`${filterName}-select-all`);
  const checkboxes = document.querySelectorAll(`.form-check-input[name="${filterName}"]`);

  if (!selectAllCheckbox || checkboxes.length === 0) return;

  // Handle 'select all' checkbox change
  selectAllCheckbox.addEventListener('change', () => {
    checkboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
    checkboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
    updateDropdownText(filterName, keepText);
//    updateDropdownCountBadge(filterName);
  });

  // Sync 'select all' checkbox with individual checkbox state
  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      selectAllCheckbox.checked = Array.from(checkboxes).every(c => c.checked);
      updateDropdownText(filterName, keepText);
//      updateDropdownCountBadge(filterName);
    });
  });

  // Initial label update
  updateDropdownText(filterName, keepText);
//  updateDropdownCountBadge(filterName);
}

/**
 * updateDateForInputType
 *
 * Updates the #cards_row_date_for input dynamically based on the selected aggregation:
 * - 'day', 'month', 'year', 'all_time'
 *
 * Behavior:
 * - Ensures the input value matches the expected format to avoid browser truncation.
 * - Disables input when aggregation is 'all_time'.
 * - Initializes input on page load based on the currently selected aggregation.
 */
function updateDateForInputType() {
  const aggregationRadios = document.querySelectorAll('input[name="cards_row_aggregation"]');
  const wrapper = document.getElementById('cards_row_date_wrapper');

  /**
   * normalizeDateValue
   *
   * Converts a raw date string into the correct format for the input type:
   * - 'day'   -> 'YYYY-MM-DD'
   * - 'month' -> 'YYYY-MM'
   * - 'year'  -> 'YYYY'
   *
   * Returns '' for invalid or empty input.
   */
  function normalizeDateValue(value, type) {
    let date = value ? new Date(value) : new Date(); // fallback to now if value empty
    if (isNaN(date)) date = new Date(); // fallback if invalid
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');

    if (type === 'month') return `${yyyy}-${mm}`;
    if (type === 'day') return `${yyyy}-${mm}-${dd}`;
    if (type === 'year') return `${yyyy}`;
    return '';
  }

  /**
   * renderInput
   *
   * Replaces the #cards_row_date_for input based on selected aggregation:
   * - 'day': type="date"
   * - 'month': type="month"
   * - 'year': Bootstrap dropdown + hidden input (ensures valid value + better UX)
   * - 'all_time': type="date" but disabled
   *
   * Normalizes the value for the input type to prevent browser truncation or invalid submissions.
   */
  function renderInput(radio) {
    const currentInput = document.getElementById('cards_row_date_for');
    let value = currentInput ? currentInput.value : '';
    let newElementHTML = '';

    switch (radio.value) {
      case 'month':
        value = normalizeDateValue(value, 'month');
        newElementHTML = `
          <input type="month" id="cards_row_date_for" name="cards_row_date_for"
            form="dashboard-filter-cards-row-form" value="${value}">
        `;
        break;

      case 'year':
        let selectedYear = normalizeDateValue(value, 'year');
        let dropdownId = 'cards_row_year_dropdown';
        let dropdownToggle = `
          <button class="btn btn-secondary dropdown-toggle" type="button"
            id="${dropdownId}" data-bs-toggle="dropdown" aria-expanded="false">
            ${selectedYear || 'Select Year'}
          </button>
        `;
        let dropdownMenu = `<ul class="dropdown-menu" aria-labelledby="${dropdownId}">`;
        for (let year = 2023; year <= 2030; year++) {
          dropdownMenu += `<li><a class="dropdown-item" href="#" data-year="${year}">${year}</a></li>`;
        }
        dropdownMenu += `</ul>`;
        let hiddenInput = `
          <input type="hidden" id="cards_row_date_for" name="cards_row_date_for"
            form="dashboard-filter-cards-row-form" value="${selectedYear}">
        `;
        newElementHTML = `<div class="dropdown">${dropdownToggle}${dropdownMenu}</div>${hiddenInput}`;
        break;

      case 'day':
      case 'all_time':
        // Use full date for 'day' to avoid truncation (YYYY-MM-DD)
        value = normalizeDateValue(value, 'day');
        newElementHTML = `
          <input type="date" id="cards_row_date_for" name="cards_row_date_for"
            form="dashboard-filter-cards-row-form" value="${value}"
            ${radio.value === 'all_time' ? 'disabled' : ''}>
        `;
        break;

      default:
        value = normalizeDateValue(value, 'month');
        newElementHTML = `
          <input type="month" id="cards_row_date_for" name="cards_row_date_for"
            form="dashboard-filter-cards-row-form" value="${value}">
        `;
    }

    wrapper.innerHTML = newElementHTML;
  }

  // Listen for aggregation changes
  aggregationRadios.forEach(radio => {
    radio.addEventListener('change', () => renderInput(radio));
  });

  // Initialize input on page load based on currently checked radio
  const checkedRadio = document.querySelector('input[name="cards_row_aggregation"]:checked');
  if (checkedRadio) renderInput(checkedRadio);
}

/**
 * Bootstrap year dropdown handler
 *
 * Updates the hidden input and dropdown label when a year is selected.
 */
document.addEventListener('click', function(e) {
  if (e.target.matches('.dropdown-item[data-year]')) {
    e.preventDefault();
    let year = e.target.getAttribute('data-year');
    document.getElementById('cards_row_date_for').value = year;
    document.getElementById('cards_row_year_dropdown').textContent = year;
  }
});


/**
 * Fade in table cell contents using CSS class `visible`
 * Useful for animations after content swap
 */
function fadeInTableCells() {
  document.querySelectorAll('.td-t9ns-text:not(.visible), .td-summary-text:not(.visible)').forEach(el => {
    requestAnimationFrame(() => el.classList.add('visible'));
  });
}

/**
 * Setup global event handlers and component initialization
 */
document.addEventListener('DOMContentLoaded', () => {
  // Initialize filter dropdowns
  setupFilterSelectAll('category');
  setupFilterSelectAll('parent_category');
  setupFilterSelectAll('cards_row_transaction_type', keepText=true);
  setupFilterSelectAll('cards_row_parent_category', keepText=true);
  setupFilterSelectAll('cards_row_category', keepText=true);
  initAggregationDropdown("cards_row_aggregation", "month", fullName=false);

  // Initial fade-in animation
  fadeInTableCells();

  // Modal initialization with config-based behavior
  initModals();

  // Prevent row clicks triggered by inner buttons/links
  preventRowClickFromButtons();

  // Add the dynamic date input initialization
  updateDateForInputType();
});

/**
 * Handle HTMX lifecycle globally
 * - Apply fade-in to swapped content
 */
document.body.addEventListener('htmx:afterSwap', () => {
  fadeInTableCells();
  preventRowClickFromButtons();

  // Re-init aggregation dropdown if it was swapped in
  initAggregationDropdown("cards_row_aggregation", "month", false);
});