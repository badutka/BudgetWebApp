import { chartOptions } from './charts_const.js';

import { renderSummariesChart } from './summaries_chart.js';
import { renderSavingsRateChart } from './savings_rate_chart.js';
import { renderCumulativeChart } from './cumulative_inc_exp_chart.js';
import { renderVolatilityTrendChart } from './volatility_trend_chart.js';
import { renderCategoriesColumnChart } from './categories_charts.js';

//  const income = chartData.map(item => parseFloat(item.income));
//  const expenses = chartData.map(item => parseFloat(item.expenses));
//  const netSavings = chartData.map(item => parseFloat(item.net_savings));
//  const endingBalance = chartData.map(item => parseFloat(item.ending_balance));

/**
 * Dispatcher
 */
function initRow(container) {
    console.log(container.id)
  if (container.id === 'dashboard-summary-container') initRow1(container);
  if (container.id === 'dashboard-categories-container') initRow2(container);
}

// Run once on initial load
document.addEventListener('DOMContentLoaded', () => {
  initRow(document.getElementById('dashboard-summary-container'));
  initRow(document.getElementById('dashboard-categories-container'));
});

// Re-run after HTMX swaps
document.body.addEventListener('htmx:afterSwap', (evt) => {
  initRow(evt.target);
});

/**
 * Row 1: summary charts
 */
function initRow1(container) {
  const balanceDataEl = container.querySelector('#summary-chart-data');
  if (!balanceDataEl) return;

  const chartData = JSON.parse(balanceDataEl.textContent);

  // Try to find the checked frequency radio for this row
  const frequencyInput = document.querySelector('input[name="summary_row_aggregation"]:checked');
  const frequency = frequencyInput ? frequencyInput.value : 'month';

  // -------------------- Summaries Chart --------------------
  const summariesSeries = [
    { label: 'Income', data: chartData.income, color: chartOptions.colors.PRIMARY },
    { label: 'Expenses', data: chartData.expenses, color: chartOptions.colors.SECONDARY },
    { label: 'Net Savings', data: chartData.net_savings, color: chartOptions.colors.TERT },
    { label: 'Accounts Balance', data: chartData.accounts_balance, color: chartOptions.colors.QUAT }
  ];
  renderSummariesChart('summaries-chart', chartData.ds, summariesSeries, frequency);

  // -------------------- Volatility Trend Chart --------------------
  const volatilitySeries = [
    {
      label: 'Income',
      mean: chartData.income_mean,
      lowerBand: chartData.income_lower_band,
      upperBand: chartData.income_upper_band,
      color: chartOptions.colors.PRIMARY
    },
    {
      label: 'Expenses',
      mean: chartData.expenses_mean,
      lowerBand: chartData.expenses_lower_band,
      upperBand: chartData.expenses_upper_band,
      color: chartOptions.colors.SECONDARY
    }
  ];
  renderVolatilityTrendChart('volatility-trend-chart', chartData.ds, volatilitySeries, frequency);

  // -------------------- Cumulative Chart --------------------
  const cumulativeSeries = [
    { label: 'Income', data: chartData.cumulative_income, color: chartOptions.colors.PRIMARY },
    { label: 'Expenses', data: chartData.cumulative_expenses, color: chartOptions.colors.SECONDARY }
  ];
  renderCumulativeChart('cumulative-chart', chartData.ds, cumulativeSeries, frequency);

  // -------------------- Savings Rate Chart --------------------
  const savingsRateSeries = [
    { label: 'Savings Rate (%)', data: chartData.savings_rate, color: chartOptions.colors.Primary }
  ];
  renderSavingsRateChart('savings-rate-chart', chartData.ds, savingsRateSeries, frequency);
}

/**
 * Row 2: (example for later charts/widgets)
 */
function initRow2(container) {
  const dataEl = container.querySelector('#categories-chart-data');
  if (!dataEl) return;

  const chartData = JSON.parse(dataEl.textContent);
    console.log(chartData);
  // Example new chart
   renderCategoriesColumnChart('categories-column-chart', chartData.parent_category, chartData.count);
}
