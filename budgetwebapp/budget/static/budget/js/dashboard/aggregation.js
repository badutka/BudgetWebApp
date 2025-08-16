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
export function initAggregationDropdown(fieldName, defaultValue = "month", { fullName = false } = {}) {
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
export function updateDateForInputType() {
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
