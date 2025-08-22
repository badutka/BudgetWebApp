import { chartOptions } from './charts_const.js';
import { generateCategories } from './chartHelpers.js';

/**
 * Render a cumulative chart in the given container
 * @param {string} containerId - ID of the HTML container
 * @param {Array<string|Date>} ds - Array of dates
 * @param {Array} seriesData - Series data [{ label, data, color }]
 * @param {string} frequency - 'day', 'month', or 'year' (default: 'month')
 */
export function renderCumulativeChart(containerId, ds, seriesData, frequency = 'month') {
  const categories = generateCategories(frequency, ds);

  Highcharts.chart(containerId, {
    chart: {
      type: 'spline',        // smooth cumulative lines
      zoomType: 'xy',
      backgroundColor: 'transparent',
      style: { fontFamily: chartOptions.font.FAMILY }
    },
    title: {
      text: '',
      style: { color: chartOptions.colors.WHITE }
    },
    xAxis: {
      categories,
      labels: {
        style: { color: chartOptions.colors.WHITE },
        rotation: chartOptions.axis.LABEL_ROTATION
      },
      tickWidth: chartOptions.axis.TICK_WIDTH,
      title: {
        text: 'ds',
        style: { color: chartOptions.colors.WHITE }
      },
      crosshair: {
        color: chartOptions.colors.CROSSHAIR,
        width: chartOptions.axis.TICK_WIDTH
      },
      lineColor: chartOptions.colors.WHITE,
      tickColor: chartOptions.colors.WHITE
    },
    yAxis: {
      title: {
        text: 'Cumulative Amount (PLN)',
        style: { color: chartOptions.colors.WHITE }
      },
      labels: {
        style: { color: chartOptions.colors.WHITE }
      },
      gridLineColor: chartOptions.colors.GRID,
      lineColor: chartOptions.colors.WHITE
    },
    legend: {
      itemStyle: { color: chartOptions.colors.WHITE }
    },
    tooltip: {
      shared: true,
      valueDecimals: 2,
      valueSuffix: ' PLN',
      backgroundColor: chartOptions.colors.TOOLTIP_BG,
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
      ...(frequency === 'day' && { xDateFormat: '%b %e, %Y' }),
      ...(frequency === 'month' && { xDateFormat: '%b %Y' }),
      ...(frequency === 'year' && { xDateFormat: '%Y' })
    },
    exporting: { enabled: false },
    series: seriesData.map(s => ({
      name: s.label,
      data: s.data,
      color: s.color,
      lineWidth: 2,
      marker: { enabled: frequency !== 'day' }  // enable for month/year
    }))
  });
}