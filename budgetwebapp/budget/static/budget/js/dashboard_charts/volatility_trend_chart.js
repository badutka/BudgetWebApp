import { chartOptions } from './charts_const.js';
import { generateCategories } from './chartHelpers.js';

/**
 * Render a volatility trend chart with 3-month averages and volatility bands
 * @param {string} containerId - ID of the HTML container
 * @param {Array<string|Date>} ds - Array of dates
 * @param {Array} seriesData - Series data [{ label, color, mean, lowerBand, upperBand }]
 * @param {string} frequency - 'day', 'month', or 'year' (default: 'month')
 */
export function renderVolatilityTrendChart(containerId, ds, seriesData, frequency = 'month') {
  const categories = generateCategories(frequency, ds);

  Highcharts.chart(containerId, {
    chart: {
      type: 'line',
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
        text: 'Volatility',
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
      backgroundColor: chartOptions.colors.TOOLTIP_BG,
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
      ...(frequency === 'day' && { xDateFormat: '%b %e, %Y' }),
      ...(frequency === 'month' && { xDateFormat: '%b %Y' }),
      ...(frequency === 'year' && { xDateFormat: '%Y' })
    },
    series: seriesData.flatMap(s => [
      {
        name: `${s.label} (3M Avg)`,
        data: s.mean,
        color: s.color,
        lineWidth: 2,
        marker: { enabled: frequency !== 'day' }
      },
      {
        name: `${s.label} Volatility Band`,
        type: 'arearange',
        linkedTo: ':previous',
        lineWidth: 0,
        fillOpacity: 0.2,
        zIndex: 0,
//        marker: { enabled: false },
        color: s.color,
        tooltip: { valueDecimals: 2 },
        data: ds.map((_, i) => [i, s.lowerBand[i], s.upperBand[i]]),
         marker: {
            enabled: false,           // hide markers normally
            states: {
              hover: {
                enabled: false        // hide markers even on hover
              }
            }
          }
      }
    ])
  });
}