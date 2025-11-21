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

    const type = el.dataset.widgetType;
    const subtype = el.dataset.widgetSubtype || 'default';
    const variant = el.dataset.widgetVariant || 'default';
    const widgetId = el.dataset.widgetId;
    const scriptEl = document.getElementById(`widget-data-${widgetId}`);

//    console.log(type)
//    console.log(subtype)
//    console.log(widgetId)
//    console.log(scriptEl)
//    console.log(variant)

    if (!type || !widgetId || !scriptEl) {
      console.warn('Skipping invalid widget:', el);
      return;
    }

    const data = JSON.parse(scriptEl.textContent);
    // Resolve renderer
    let renderer = widgetRenderers?.[type]?.[subtype];

    if (renderer) {
      // If this subtype is a function, no variants exist → use directly
      if (typeof renderer === 'function') {
        // OK: timeseries, etc.
      } else if (typeof renderer === 'object') {
        // Subtype supports variants
        renderer = renderer[variant] || renderer.default;
      }
    }

    if (typeof renderer === 'function') {
      const chartContainer = el.querySelector('.chart-container');
      renderer(chartContainer, data);
      el.dataset.initialized = 'true';
    } else {
      console.warn(`No renderer found for widget: ${type}:${subtype}:${variant}`);
    }
  });
}