import { widgetRenderers } from './index.js';

/**
 * Initialize all widgets inside a given container (or the whole document).
 * This function is safe to call multiple times — it won’t re-initialize widgets.
 */
export function initWidgets(container = document) {
  const widgets = container.querySelectorAll('.widget');

  widgets.forEach(el => {
    // Prevent re-initialization
    if (el.dataset.initialized === 'true') return;
    console.log(el)
    const type = el.dataset.widgetType;
    const subtype = el.dataset.widgetSubtype || 'default';
    const widgetId = el.dataset.widgetId;
    const scriptEl = document.getElementById(`widget-data-${widgetId}`);

    console.log(type)
    console.log(subtype)
    console.log(widgetId)
    console.log(scriptEl)

    if (!type || !widgetId || !scriptEl) {
      console.warn('Skipping invalid widget:', el);
      return;
    }

    const data = JSON.parse(scriptEl.textContent);
    const renderer = widgetRenderers?.[type]?.[subtype];

    if (typeof renderer === 'function') {
      const chartContainer = el.querySelector('.chart-container');
      renderer(chartContainer, data);
      el.dataset.initialized = 'true';
    } else {
      console.warn(`No renderer found for widget: ${type}:${subtype}`);
    }
  });
}