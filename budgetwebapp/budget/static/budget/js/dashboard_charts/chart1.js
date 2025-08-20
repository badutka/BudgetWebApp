import { chartOptions } from './charts_const.js';

document.addEventListener('DOMContentLoaded', () => {
  const chartData = JSON.parse(
    document.getElementById('balance-chart-data').textContent
  );

//  const income = chartData.map(item => parseFloat(item.income));
//  const expenses = chartData.map(item => parseFloat(item.expenses));
//  const netSavings = chartData.map(item => parseFloat(item.net_savings));
//  const endingBalance = chartData.map(item => parseFloat(item.ending_balance));
    const income = chartData.income;
    const expenses = chartData.expenses;
    const netSavings = chartData.net_savings;
    const endingBalance = chartData.ending_balance;
    const savingsRate = chartData.savings_rate;
    console.log(expenses)

  Highcharts.chart('balance-chart', {
    chart: {
      type: 'line',
      zoomType: 'xy',  // allows horizontal zooming
//    backgroundColor: '#111827', // match container
//    backgroundColor: '#0c1833', // match container
//    backgroundColor: '#091d4b', // match container
      backgroundColor: 'transparent', // match container
      style: { fontFamily: chartOptions.font.FAMILY }
    },
    title: {
      text: '',
      style: { color: chartOptions.colors.WHITE }
    },
    xAxis: {
      categories: chartOptions.months,
      labels: {
        style: { color: chartOptions.colors.WHITE }, // tailwind slate-200
        rotation: chartOptions.axis.LABEL_ROTATION  // or try -45 or 45 for diagonal
      },
//    minorTicks: true,
//    minorTickInterval: 0.5,  // show tick for every month (default)
//    tickmarkPlacement: 'on',  // align ticks with category labels
      tickWidth: chartOptions.axis.TICK_WIDTH,
      title: {
        text: 'Month',
        style: { color: chartOptions.colors.WHITE }
      },
      crosshair: {
        color: chartOptions.colors.CROSSHAIR,
        width: chartOptions.axis.TICK_WIDTH,
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
//    gridLineColor: '#112147', // dark gray grid lines
      gridLineColor: chartOptions.colors.GRID, // dark gray grid lines
      lineColor: chartOptions.colors.WHITE,
//    gridLineColor: 'blue',
//    lineColor: 'blue',
      minorTickInterval: chartOptions.axis.MINOR_TICK_INTERVAL,
      tickInterval: chartOptions.axis.TICK_INTERVAL_AMOUNT,
    },
    legend: {
      itemStyle: { color: chartOptions.colors.WHITE }
    },
    tooltip: {
      shared: true,
      valueDecimals: 2,
      valueSuffix: ' PLN',
//    stickOnContact: false
//    backgroundColor: '#1f2937',  // dark tooltip
      backgroundColor: chartOptions.colors.TOOLTIP_BG, // dark navy with slight transparency
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
    },
    exporting: {
      enabled: false
    },
    series: [
      { name: 'Income', data: income },
      { name: 'Expenses', data: expenses },
      { name: 'Net Savings', data: netSavings },
      { name: 'Ending Balance', data: endingBalance }
    ]
  });

  Highcharts.chart('balance-chart2', {
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
      categories: chartOptions.months,
      labels: {
        style: { color: chartOptions.colors.WHITE },
        rotation: chartOptions.axis.LABEL_ROTATION
      },
      tickWidth: chartOptions.axis.TICK_WIDTH,
      title: {
        text: 'Month',
        style: { color: chartOptions.colors.WHITE }
      },
      crosshair: {
        color: chartOptions.colors.CROSSHAIR,
        width: chartOptions.axis.TICK_WIDTH,
      },
      lineColor: chartOptions.colors.WHITE,
      tickColor: chartOptions.colors.WHITE
    },
    yAxis: {
      title: {
        text: 'Savings Rate (%)',
        style: { color: chartOptions.colors.WHITE }
      },
      labels: {
        format: '{value}%',   // show % in axis labels
        style: { color: chartOptions.colors.WHITE }
      },
      tickInterval: chartOptions.axis.TICK_INTERVAL_PERCENT, // 50% increments
      gridLineColor: chartOptions.colors.GRID,
      lineColor: chartOptions.colors.WHITE
    },
    legend: {
      itemStyle: { color: chartOptions.colors.WHITE }
    },
    tooltip: {
      shared: true,
      valueDecimals: 2,
      valueSuffix: '%',       // show % in tooltip
      backgroundColor: chartOptions.colors.TOOLTIP_BG,
      style: { color: chartOptions.colors.TEXT },
      borderColor: chartOptions.colors.WHITE,
      borderWidth: chartOptions.tooltip.BORDER_WIDTH,
    },
    series: [
      { name: 'Savings Rate (%)', data: savingsRate }
    ]
  });
});