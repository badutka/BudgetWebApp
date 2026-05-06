import { renderTimeSeriesChart, renderPieChart, renderTimeSeriesChart2 } from './charts.js';

export const widgetRenderers = {
  chart: {
    pie: renderPieChart,
    timeseries: renderTimeSeriesChart,
    timeseries2: renderTimeSeriesChart2,
  },
};