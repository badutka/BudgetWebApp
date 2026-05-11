import { initWidgets } from './widgets/initWidgets.js';

function initSingleValueDropdown(dropdownId) {

  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;

  const items = dropdown.querySelectorAll('.dropdown-single-value-generic-menu .dropdown-item');

  items.forEach(item => {

    item.addEventListener('click', function () {

      const label = dropdown.querySelector('.label');
      const btnIcon = dropdown.querySelector('.btn-icon');

      const itemLabel = this.textContent.trim();
      const itemIcon = this.querySelector('i');

      // update label
      if (label) {
        label.textContent = itemLabel;
      }

      // update icon
      if (itemIcon && btnIcon) {

        const iconClass = [...itemIcon.classList]
          .find(cls => cls.startsWith('fa-') && cls !== 'fas');

        btnIcon.className = `fas ${iconClass} btn-icon`;
      }

      // active state
      dropdown.querySelectorAll('.dropdown-item')
        .forEach(i => i.classList.remove('active'));

      this.classList.add('active');

    });

  });

}

// expose globally
window.initSingleValueDropdown = initSingleValueDropdown;

document.addEventListener('DOMContentLoaded', () => {
  initWidgets();
});

