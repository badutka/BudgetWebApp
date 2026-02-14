import { renderTimeSeriesChart, renderPieChart } from './charts.js';

export const widgetRenderers = {
  chart: {
    pie: renderPieChart,
    timeseries: renderTimeSeriesChart,
  },
};