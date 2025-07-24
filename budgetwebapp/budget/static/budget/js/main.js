
//var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
//var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
//  return new bootstrap.Tooltip(tooltipTriggerEl)
//})

function preventRowClickFromButtons() {
  document.querySelectorAll("td a, td button").forEach(el => {
    el.addEventListener("click", function (e) {
      e.stopPropagation(); // prevents the tr click from firing
    });
  });
}

function initModal(modalId, modalDialog) {
  //https://blog.benoitblanchon.fr/django-htmx-modal-form/
  const modalElement = document.getElementById(modalId);
  if (!modalElement) return;

  const modal = new bootstrap.Modal(modalElement);

  htmx.on("htmx:afterSwap", (e) => {
    if (e.detail.target.id === modalDialog) {
      modal.show();
    }
  });

  htmx.on("htmx:beforeSwap", (e) => {
    if (e.detail.target.id === modalDialog && !e.detail.xhr.response) {
      modal.hide();
      document.location.reload();
      e.detail.shouldSwap = false;
    }
  });

  htmx.on("hidden.bs.modal", () => {
    const dialog = document.getElementById(modalDialog);
    if (dialog) dialog.innerHTML = "";
  });

   // Only render chart if this specific modal was updated
  document.addEventListener("htmx:afterSwap", function(evt) {
    if (evt.target && evt.target.querySelector('#categoryChartModal')) {
      renderChartInModal();
    }
  });

}

// ===== Filter Dropdown Logic =====
function updateDropdownText(filterName) {
  const checkboxes = document.querySelectorAll(`.form-check-input[name="${filterName}"]`);
  const dropdownButton = document.getElementById(`${filterName}DropdownButton`);
  if (!dropdownButton) return;

  const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
  dropdownButton.textContent = `${checkedCount} selected`;
}

function setupFilterSelectAll(filterName) {
  const selectAllCheckbox = document.getElementById(`${filterName}-select-all`);
  const checkboxes = document.querySelectorAll(`.form-check-input[name="${filterName}"]`);
  if (!selectAllCheckbox || checkboxes.length === 0) return;

  // Select all
  selectAllCheckbox.addEventListener('change', () => {
    checkboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
    checkboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
    updateDropdownText(filterName);
  });

  // Sync select-all checkbox
  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      selectAllCheckbox.checked = Array.from(checkboxes).every(c => c.checked);
      updateDropdownText(filterName);
    });
  });

  updateDropdownText(filterName);
}

// ===== Fade-in Animation =====
function fadeInTableCells() {
  document.querySelectorAll('.td-t9ns-text:not(.visible), .td-summary-text:not(.visible)').forEach(el => {
    requestAnimationFrame(() => el.classList.add('visible'));
  });
}

// ===== App Init =====
document.addEventListener('DOMContentLoaded', () => {
  // Init filter logic
  setupFilterSelectAll('category');
  setupFilterSelectAll('parent_category');

  // Initial animation
  fadeInTableCells();

  // Init modal behavior
  initModal('modal-transactions-by-cat', 'dialog-transactions-by-cat');
  initModal('modal', 'dialog');

  // Prevent event bubbling on buttons/links inside TDs
  preventRowClickFromButtons();
});

// ===== HTMX Lifecycle Hooks =====
document.body.addEventListener('htmx:afterSwap', (e) => {
  fadeInTableCells();

  // Also re-bind click handler when new content is swapped in
  preventRowClickFromButtons();
});

//// check / uncheck all checklist boxes
//document.addEventListener('DOMContentLoaded', function () {
//    const selectAllCheckbox = document.getElementById('category-select-all');
//    const categoryCheckboxes = document.querySelectorAll('.form-check-input[name="category"]');
//    const form = document.getElementById('transaction-filter-form');
//
//    // Select all on first load if no category param is present
//    // Use this if overriding filtering method (filter_category) to not show any results with no checkboxed values.
////    if (!window.location.search.includes('category=')) {
////        categoryCheckboxes.forEach(cb => cb.checked = true);
////        // Submit after setting them
////        categoryCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
////    }
//
//    // When "Select All" is toggled
//    selectAllCheckbox.addEventListener('change', function () {
//        categoryCheckboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
//
//        // 🔥 Trigger a real 'change' event on one of the boxes to activate HTMX
////        if (categoryCheckboxes.length > 0) {
//            categoryCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
////        }
//    });
//
//    // When any category checkbox is manually changed
//    categoryCheckboxes.forEach(cb => {
//        cb.addEventListener('change', function () {
//            const allChecked = Array.from(categoryCheckboxes).every(cb => cb.checked);
//            selectAllCheckbox.checked = allChecked;
//        });
//    });
//});


//$(document).ready(function() {
//    function handleDropdownChange(dropdownId, outputId) {
//        $(dropdownId).change(function() {
//            var selectedValue = $(this).val();
//            $.ajax({
//                url: '/transactions/',
//                data: {
//                    'selected_value': selectedValue
//                },
//                dataType: 'json',
////                success: function(data) {
////                    $(outputId).html(data.response);
////                }
//            });
//        });
//    }
//
//    handleDropdownChange('#dropdown', '#transactions-table');
////    handleDropdownChange('#dropdown2', '#output2');
//});