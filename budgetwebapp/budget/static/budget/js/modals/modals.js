import { renderChartInModal } from './charts.js';

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
export function initModals() {
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
