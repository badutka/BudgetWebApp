
//var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
//var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
//  return new bootstrap.Tooltip(tooltipTriggerEl)
//})

//https://blog.benoitblanchon.fr/django-htmx-modal-form/
const modal = new bootstrap.Modal(document.getElementById("modal"))

htmx.on("htmx:afterSwap", (e) => {
  // Response targeting #dialog => show the modal
  if (e.detail.target.id == "dialog") {
    modal.show()
  }
})

htmx.on("htmx:beforeSwap", (e) => {
  // Empty response targeting #dialog => hide the modal
  if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
    modal.hide()
    document.location.reload();
    e.detail.shouldSwap = false
  }
})

htmx.on("hidden.bs.modal", () => {
  document.getElementById("dialog").innerHTML = ""
})

// check / uncheck all checklist boxes
document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('category-select-all');
    const categoryCheckboxes = document.querySelectorAll('.form-check-input[name="category"]');
    const form = document.getElementById('transaction-filter-form');

    // Select all on first load if no category param is present
    // Use this if overriding filtering method (filter_category) to not show any results with no checkboxed values.
//    if (!window.location.search.includes('category=')) {
//        categoryCheckboxes.forEach(cb => cb.checked = true);
//        // Submit after setting them
//        categoryCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
//    }

    // When "Select All" is toggled
    selectAllCheckbox.addEventListener('change', function () {
        categoryCheckboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);

        // 🔥 Trigger a real 'change' event on one of the boxes to activate HTMX
//        if (categoryCheckboxes.length > 0) {
            categoryCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
//        }
    });

    // When any category checkbox is manually changed
    categoryCheckboxes.forEach(cb => {
        cb.addEventListener('change', function () {
            const allChecked = Array.from(categoryCheckboxes).every(cb => cb.checked);
            selectAllCheckbox.checked = allChecked;
        });
    });
});


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