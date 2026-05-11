import { initWidgets } from './widgets/initWidgets.js';

function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}

document.body.addEventListener('htmx:configRequest', function (event) {
  const token = getCSRFToken();
  if (token) {
    event.detail.headers['X-CSRFToken'] = token;
  }
});

document.addEventListener('click', function (e) {

  const item = e.target.closest('.dropdown-single-value-generic .dropdown-item');
  if (!item) return;

  const dropdown = item.closest('.dropdown-single-value-generic');
  if (!dropdown) return;

  const label = dropdown.querySelector('.label');
  const btnIcon = dropdown.querySelector('.btn-icon');

  const itemLabel = item.textContent.trim();
  const itemIcon = item.querySelector('i');

  // update label
  if (label) label.textContent = itemLabel;

  // update icon
  if (itemIcon && btnIcon) {
    const iconClass = [...itemIcon.classList]
      .find(cls => cls.startsWith('fa-') && cls !== 'fas');

    btnIcon.className = `fas ${iconClass} btn-icon`;
  }

  // active state
  dropdown.querySelectorAll('.dropdown-item')
    .forEach(i => i.classList.remove('active'));

  item.classList.add('active');

});

document.addEventListener('DOMContentLoaded', () => {
  initWidgets();
});

