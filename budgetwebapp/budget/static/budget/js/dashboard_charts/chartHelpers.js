import { chartOptions } from './charts_const.js';

/**
 * Generate x-axis labels based on the data frequency.
 *
 * - For 'day', returns the dates as-is.
 * - For 'month', returns formatted labels like "May 2024", including the year to avoid confusion
 *   when the data spans multiple years.
 * - For 'year', returns the year as a string.
 *
 * @param {string} frequency - The frequency of the data: 'day', 'month', or 'year'.
 * @param {Array<string|Date>} dsArray - Array of date strings or Date objects used for the x-axis.
 * @returns {Array<string>} An array of category labels for the x-axis.
 */
export function generateCategories(frequency, dsArray) {
  if (frequency === 'day') {
    return dsArray; // use actual dates
  } else if (frequency === 'month') {
    return dsArray.map(d => {
      const date = new Date(d);
      const month = chartOptions.months[date.getMonth()]; // get month name
      const year = date.getFullYear();
      return `${month} ${year}`;
    });
  } else if (frequency === 'year') {
    return dsArray.map(d => new Date(d).getFullYear().toString());
  }
  return [];
}

/**
 * Returns a human-readable label for the chart's X-axis
 * based on the selected data aggregation frequency.
 *
 * @param {string} frequency - The aggregation frequency.
 *   Expected values: 'day', 'month', or 'year'.
 *
 * @returns {string} - The corresponding X-axis label:
 *   'Day', 'Month', 'Year', or a fallback ('ds') if unknown.
 *
 * @example
 * getXAxisLabel('day');   // "Day"
 * getXAxisLabel('month'); // "Month"
 * getXAxisLabel('year');  // "Year"
 */
export function getXAxisLabel(frequency) {
  switch (frequency) {
    case 'day':
      return 'Day';
    case 'month':
      return 'Month';
    case 'year':
      return 'Year';
    default:
      return 'ds'; // fallback label
  }
}