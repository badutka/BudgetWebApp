import { chartOptions } from './charts_const.js';
import { generateCategories } from './chartHelpers.js';

/**
 * Render a Highcharts spline chart for summarized data.
 *
 * - Automatically generates x-axis categories based on frequency.
 * - Enables markers for 'month' and 'year' data, disables markers for 'day'.
 * - Formats tooltips according to frequency.
 *
 * @param {string} containerId - The DOM element ID where the chart will be rendered.
 * @param {Array<string|Date>} ds - Array of dates for the x-axis.
 * @param {Array<Object>} seriesData - Array of series objects:
 *   - label: {string} series name
 *   - data: {Array<number>} series values
 *   - color: {string} color for the series line
 * @param {string} [frequency='month'] - Frequency of the data: 'day', 'month', or 'year'.
 */
export function renderSummariesChart(containerId, ds, seriesData, frequency = 'month') {
  // Generate x-axis categories
  const categories = generateCategories(frequency, ds);

  Highcharts.chart(containerId, {
    chart: {
      type: 'spline',            // smooth line chart
      zoomType: 'xy',            // allows horizontal zooming
      // backgroundColor: '#111827', // match container
      // backgroundColor: '#0c1833', // match container
      // backgroundColor: '#091d4b', // match container
      backgroundColor: 'transparent', // match container
      style: { fontFamily: chartOptions.font.FAMILY }
    },
    title: {
      text: '',                // no title
      style: { color: chartOptions.colors.WHITE }
    },
    xAxis: {
      categories,               // actual dates for daily, else months/years
      labels: {
        style: { color: chartOptions.colors.WHITE },
        rotation: chartOptions.axis.LABEL_ROTATION  // diagonal labels if needed
      },
      // minorTicks: true,
      // minorTickInterval: 0.5,  // show tick for every month (default)
      // tickmarkPlacement: 'on',  // align ticks with category labels
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
        text: 'Amount (PLN)',
        style: { color: chartOptions.colors.WHITE }
      },
      labels: {
        style: { color: chartOptions.colors.WHITE } // tailwind slate-200
      },
      tickWidth: 0.5,
      tickColor: chartOptions.colors.WHITE,
      lineWidth: chartOptions.axis.LINE_WIDTH,
      // gridLineColor: '#112147', // dark gray grid lines
      gridLineColor: chartOptions.colors.GRID, // dark gray grid lines
      lineColor: chartOptions.colors.WHITE,
      // gridLineColor: 'blue',
      // lineColor: 'blue',
      minorTickInterval: chartOptions.axis.MINOR_TICK_INTERVAL,
      tickInterval: chartOptions.axis.TICK_INTERVAL_AMOUNT
    },
    legend: {
      itemStyle: { color: chartOptions.colors.WHITE }
    },
    tooltip: {
      shared: true,
      valueDecimals: 2,
      valueSuffix: ' PLN',
      // stickOnContact: false
      // backgroundColor: '#1f2937',  // dark tooltip
      backgroundColor: chartOptions.colors.TOOLTIP_BG, // dark navy with slight transparency
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
      ...(frequency === 'day' && { xDateFormat: chartOptions.dateFormats.dateFormatFull }),
      ...(frequency === 'month' && { xDateFormat: chartOptions.dateFormats.dateFormatMonth }),
      ...(frequency === 'year' && { xDateFormat: chartOptions.dateFormats.dateFormatyear })
    },
    exporting: {
      enabled: false
    },
    series: seriesData.map(s => ({
      name: s.label,
      data: s.data,
      color: s.color,
      lineWidth: 2,
      marker: { enabled: frequency !== 'day' } // smooth lines without markers
    }))
  });
};
