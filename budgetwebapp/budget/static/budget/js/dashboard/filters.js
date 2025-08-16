export function updateDropdownCountBadge(filterName) {
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
export function setupFilterSelectAll(filterName, { keepText = false } = {}) {
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
