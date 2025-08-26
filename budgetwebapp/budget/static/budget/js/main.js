// main.js

import { preventRowClickFromButtons, fadeInTableCells } from './tables/tables.js';
import { initModals } from './modals/modals.js';
import { initAggregationDropdown, updateDateForInputType } from './dashboard/aggregation.js';
import { setupFilterSelectAll } from './dashboard/filters.js';

/**
 * Setup global event handlers and component initialization
 */
 // --------- DOM READY ---------
document.addEventListener('DOMContentLoaded', () => {
  // Filters (used in transactions + dashboard)
  setupFilterSelectAll('category');
  setupFilterSelectAll('parent_category');
  setupFilterSelectAll('cards_row_transaction_type', { keepText: true });
  setupFilterSelectAll('cards_row_parent_category', { keepText: true });
  setupFilterSelectAll('cards_row_category', { keepText: true });

  // summary charts
  setupFilterSelectAll('summary_row_transaction_type', { keepText: true });
  setupFilterSelectAll('summary_row_parent_category', { keepText: true });
  setupFilterSelectAll('summary_row_category', { keepText: true });

  // Dashboard-only logic
  initAggregationDropdown("cards_row_aggregation", "month", { fullName: false });
  // Add the dynamic date input initialization
  updateDateForInputType();

  // UI polish
  // Initial fade-in animation
  fadeInTableCells();
  // Prevent row clicks triggered by inner buttons/links
  preventRowClickFromButtons();

  // Modal initialization with config-based behavior
  initModals();

});

/**
 * Handle HTMX lifecycle globally
 * - Apply fade-in to swapped content
 */
document.body.addEventListener('htmx:afterSwap', () => {
  fadeInTableCells();
  preventRowClickFromButtons();

  // Re-init aggregation dropdown if it was swapped in
  initAggregationDropdown("cards_row_aggregation", "month", { fullName: false });
});