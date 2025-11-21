import { renderTimeSeriesChart, renderPieChart } from './charts.js';

export const widgetRenderers = {
  chart: {
    pie: {
      main_account_allocation: renderPieChart,
      ike_account_allocation: renderPieChart,
      default: renderPieChart,
    },
    timeseries: renderTimeSeriesChart,
  },
};