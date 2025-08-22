import { chartOptions } from './charts_const.js';

import { renderSummariesChart } from './summaries_chart.js';
import { renderSavingsRateChart } from './savings_rate_chart.js';
import { renderCumulativeChart } from './cumulative_inc_exp_chart.js';
import { renderVolatilityTrendChart } from './volatility_trend_chart.js';

//  const income = chartData.map(item => parseFloat(item.income));
//  const expenses = chartData.map(item => parseFloat(item.expenses));
//  const netSavings = chartData.map(item => parseFloat(item.net_savings));
//  const endingBalance = chartData.map(item => parseFloat(item.ending_balance));


document.addEventListener('DOMContentLoaded', () => {
  const chartData = JSON.parse(
    document.getElementById('balance-chart-data').textContent
  );

  const frequency = 'month';

  // Extract series data for summaries chart
  const income = chartData.income;
  const expenses = chartData.expenses;
  const netSavings = chartData.net_savings;
  const accountsBalance = chartData.accounts_balance;

  const summariesSeries = [
    { label: 'Income', data: income, color: chartOptions.colors.Primary },
    { label: 'Expenses', data: expenses, color: chartOptions.colors.Secondary },
    { label: 'Net Savings', data: netSavings, color: chartOptions.colors.Tertiary },
    { label: 'Accounts Balance', data: accountsBalance, color: chartOptions.colors.Quaternary }
  ];

  renderSummariesChart('summaries-chart', chartData.ds, summariesSeries, frequency);

  // -------------------- Volatility Trend Chart --------------------
  const incomeVolatility = {
    label: 'Income',
    mean: chartData.income_mean,
    lowerBand: chartData.income_lower_band,
    upperBand: chartData.income_upper_band,
    color: chartOptions.colors.PRIMARY
  };

  const expensesVolatility = {
    label: 'Expenses',
    mean: chartData.expenses_mean,
    lowerBand: chartData.expenses_lower_band,
    upperBand: chartData.expenses_upper_band,
    color: chartOptions.colors.SECONDARY
  };

  const volatilitySeries = [incomeVolatility, expensesVolatility];

  renderVolatilityTrendChart('volatility-trend-chart', chartData.ds, volatilitySeries, frequency);

  // -------------------- Cumulative Chart --------------------
  const cumulativeIncome = chartData.cumulative_income;
  const cumulativeExpenses = chartData.cumulative_expenses;

  const cumulativeSeries = [
    { label: 'Income', data: cumulativeIncome, color: chartOptions.colors.PRIMARY },
    { label: 'Expenses', data: cumulativeExpenses, color: chartOptions.colors.SECONDARY }
  ];

  renderCumulativeChart('cumulative-chart', chartData.ds, cumulativeSeries, frequency);

  // -------------------- Savings Rate Chart --------------------
  const savingsRate = chartData.savings_rate;

  const savingsRateSeries = [
  { label: 'Savings Rate (%)', data: savingsRate, color: chartOptions.colors.Primary }
  ];

  renderSavingsRateChart('savings-rate-chart', chartData.ds, savingsRateSeries, frequency);
});


