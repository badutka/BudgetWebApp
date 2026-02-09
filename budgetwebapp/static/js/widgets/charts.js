import { chartOptions } from './charts_const.js';

export function renderTimeSeriesChart(container, data) {
//  const investedSeries = data.date.map((d, i) => [Date.parse(d), data.invested_value[i]]);
//  const totalSeries = data.date.map((d, i) => [Date.parse(d), data.portfolio_value[i]]);
//  const gainSeries = data.date.map((d, i) => [Date.parse(d), data.net_gain[i]]);

    const COLOR_POOL = [
      chartOptions.colors.PRIMARY,
      chartOptions.colors.SECONDARY,
      chartOptions.colors.TERT,
      chartOptions.colors.QUAT,
    ];

    const dates = data.date;
    const seriesData = data.series;
    const meta = data.series_meta || {};

  const series = Object.keys(seriesData).map((key, index) => {

    const color = COLOR_POOL[index % COLOR_POOL.length];

    const points = dates.map((d, i) => [
      Date.parse(d),
      seriesData[key][i]
    ]);

    const name =
      meta[key]?.name ||
      key; // defaultLabel(key)

    return {
      name,
      data: points,
      color,

      fillColor: {
        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
        stops: [
          [0, Highcharts.color(color).setOpacity(0.15).get('rgba')],
          [1, Highcharts.color(color).setOpacity(0).get('rgba')]
        ]
      }
    };
  });

Highcharts.chart(container, {
    chart: {
      type: 'areaspline',            // smooth line chart
      zoomType: 'xy',            // allows horizontal zooming
      backgroundColor: 'transparent', // match container
      style: { fontFamily: chartOptions.font.FAMILY },
    },
    title: {
      text: '',                // no title
      style: { color: chartOptions.colors.WHITE }
    },
    xAxis: {
      type: 'datetime',
      labels: {
        style: { color: chartOptions.colors.WHITE },
        rotation: chartOptions.axis.LABEL_ROTATION  // diagonal labels if needed
      },
      // minorTicks: true,
      // minorTickInterval: 0.5,  // show tick for every month (default)
      // tickmarkPlacement: 'on',  // align ticks with category labels
      tickWidth: chartOptions.axis.TICK_WIDTH,
      title: {
        text: 'x axis label',
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
      backgroundColor: chartOptions.colors.TOOLTIP_BG,
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH
    },
    exporting: {
      enabled: false
    },
      series: series
});
};

export function renderPieChart(container, data) {
  if (!container) {
    console.warn("Pie chart container missing");
    return;
  }

  const { labels, values } = data;

  const pieData = labels.map((label, i) => ({
    name: label,
    y: values[i],
    color: chartOptions.PIE_ALLOC_COLORS[label] || undefined   // fallback to Highcharts
  }))//.sort((a, b) => b.y - a.y); // descending

  Highcharts.chart(container, {
    chart: {
      type: 'pie',
      backgroundColor: 'transparent',
      style: {
        fontFamily: chartOptions.font.FAMILY
      }
    },
    title: { text: '' },

    tooltip: {
      pointFormat: '<b>Allocation: {point.percentage:.2f}%</b><br>Amount: {point.y:.0f} PLN',
      backgroundColor: chartOptions.colors.TOOLTIP_BG,
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
      style: { color: chartOptions.colors.TEXT }
    },

    legend: {
      itemStyle: { color: chartOptions.colors.WHITE }
    },

    plotOptions: {
      pie: {
        allowPointSelect: true,
        cursor: 'pointer',
        borderColor: chartOptions.colors.WHITE,
        dataLabels: {
          enabled: true,
          style: {
            color: chartOptions.colors.WHITE
          },
//          distance: 20,           // move labels outside slices
          crop: false,            // don’t hide labels outside plot area
          alignTo: 'plotEdges',
//          overflow: 'allow',      // allow labels to overflow outside chart
//          connectorColor: chartOptions.colors.WHITE, // line connecting label to slice
          formatter: function () {
            return `${this.point.name}<br>${this.percentage.toFixed(2)}%<br>${this.point.y.toFixed(0)} PLN`;
          }
        },
        showInLegend: true,
      }
    },

//    legend: {
//        layout: 'vertical',
//        align: 'left',
//        verticalAlign: 'top',
////        x: -40,
////        y: 80,
//        floating: true,
//        color: 'white',
//        borderWidth: 0.5,
////        backgroundColor: 'var(--highcharts-background-color, #ffffff)',
//        shadow: true
//    },

    series: [
      {
        name: 'Value',
        data: pieData,
        dataSorting: {
            enabled: true,
            sortKey: 'y'
        },
      }
    ],

    exporting: { enabled: false }
  });
}