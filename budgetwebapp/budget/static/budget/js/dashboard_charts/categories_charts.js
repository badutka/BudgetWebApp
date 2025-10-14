import { chartOptions } from './charts_const.js';

export function renderCategoriesColumnChart(containerId, categories, counts) {
      Highcharts.chart(containerId, {
      chart: {
          type: 'column',
//          zoomType: 'xy',
          backgroundColor: 'transparent',
          style: { fontFamily: chartOptions.font.FAMILY }
        },
      title: {
        text: ''
      },
      xAxis: {
        categories: categories,
//        crosshair: true,
        labels: {
            style: { color: chartOptions.colors.WHITE },
            rotation: chartOptions.axis.LABEL_ROTATION
        },
      },
      yAxis: {
        min: 0,
        title: {
          text: 'Number of transactions',
          style: { color: chartOptions.colors.WHITE }
        },
        labels: {
            style: { color: chartOptions.colors.WHITE }
        },
        tickInterval: 10,
        gridLineColor: chartOptions.colors.GRID,
        lineColor: chartOptions.colors.WHITE
      },
      tooltip: {
        backgroundColor: chartOptions.colors.TOOLTIP_BG,
        style: { color: chartOptions.colors.TEXT },
        borderColor: chartOptions.colors.WHITE,
        borderWidth: chartOptions.tooltip.BORDER_WIDTH,
        headerFormat: '<b>{point.key}:</b><br>',
        pointFormat: 'Number of transactions: {point.y}'
      },
      exporting: { enabled: false },
      legend: {
          itemStyle: {
            color: chartOptions.colors.WHITE,
//            fontWeight: 'bold'
          }
        },
      series: [{
        name: 'Parent Categories Transactions',
        data: counts,
        borderColor: '#1DE9B6',
        borderWidth: 1,
        borderRadius: 5,
//        color: '#4FC3F7',
      }]
    });
}