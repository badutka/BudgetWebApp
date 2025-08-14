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
  setupFilterSelectAll('cards_row_transaction_type', true);
  setupFilterSelectAll('cards_row_parent_category', true);
  setupFilterSelectAll('cards_row_category', true);

  // Initial fade-in animation
  fadeInTableCells();

  // Modal initialization with config-based behavior
  initModals();

  // Prevent row clicks triggered by inner buttons/links
  preventRowClickFromButtons();
});

/**
 * Handle HTMX lifecycle globally
 * - Apply fade-in to swapped content
 */
document.body.addEventListener('htmx:afterSwap', () => {
  fadeInTableCells();
  preventRowClickFromButtons();
  // No need to re-bind row button click logic thanks to delegation
});