/**
 * Prevents clicks on buttons/links inside table cells from triggering row-level events.
 * Re-applies after HTMX swaps in case new rows are injected.
 */
export function preventRowClickFromButtons() {
  document.querySelectorAll("td a, td button, .dashboard-card .refresh-button").forEach(el => {
    el.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevents the <tr> click from firing
    });
  });
}


/**
 * Fade in table cell contents using CSS class `visible`
 * Useful for animations after content swap
 */
export function fadeInTableCells() {
  document.querySelectorAll('.td-t9ns-text:not(.visible), .td-summary-text:not(.visible)').forEach(el => {
    requestAnimationFrame(() => el.classList.add('visible'));
  });
}
