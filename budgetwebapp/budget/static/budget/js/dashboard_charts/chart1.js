import { months } from './charts_const.js';

document.addEventListener('DOMContentLoaded', () => {
  const chartData = JSON.parse(
    document.getElementById('balance-chart-data').textContent
  );

  const income = chartData.map(item => parseFloat(item.income));
  const expenses = chartData.map(item => parseFloat(item.expenses));
  const netSavings = chartData.map(item => parseFloat(item.net_savings));
  const endingBalance = chartData.map(item => parseFloat(item.ending_balance));

  Highcharts.chart('balance-chart', {
  chart: {
    type: 'line',
    zoomType: 'xy',  // allows horizontal zooming
//    backgroundColor: '#111827', // match container
//    backgroundColor: '#0c1833', // match container
//    backgroundColor: '#091d4b', // match container
    backgroundColor: 'transparent', // match container
    style: {
      fontFamily: 'Arial, sans-serif'
    }
  },
  title: {
    text: '2025 Monthly Financial Overview',
    style: {color: '#ffffff'}
  },
  xAxis: {
    categories: months,
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      },
      rotation: -45,  // or try -45 or 45 for diagonal
    },
//    minorTicks: true,
//    minorTickInterval: 0.5,  // show tick for every month (default)
//    tickmarkPlacement: 'on',  // align ticks with category labels
    tickWidth: 1,
    title: {
        text: 'Month',
        style: {color: '#ffffff'}
    },
    crosshair: {
      color: '#5181B8',
      width: 1,
    },
    lineColor: '#ffffff',
    tickColor: '#ffffff'
  },
  yAxis: {
    title: {
      text: 'Amount (PLN)',
      style: {
        color: '#ffffff'
      }
    },
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      }
    },
    tickWidth: 0.5,
    tickColor: '#ffffff',
    lineWidth: 1,
//    gridLineColor: '#112147', // dark gray grid lines
    gridLineColor: '#303f53', // dark gray grid lines
    lineColor: '#ffffff',
//    gridLineColor: 'blue',
//    lineColor: 'blue',
    minorTickInterval: 5000,
    tickInterval: 5000,
  },
  legend: {
    itemStyle: {
      color: '#ffffff'
    }
  },
  tooltip: {
    shared: true,
    valueDecimals: 2,
    valueSuffix: ' PLN',
//    stickOnContact: false
//    backgroundColor: '#1f2937',  // dark tooltip
      backgroundColor: 'rgba(15, 23, 42, 0.6)', // dark navy with slight transparency
    style: {
//      color: '#f9fafb'
      color: '#f9fafb'
    },
    borderColor: '#ffffff',
    borderWidth: 0.1,
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
    zoomType: 'xy',  // allows horizontal zooming
//    backgroundColor: '#111827', // match container
//    backgroundColor: '#0c1833', // match container
//    backgroundColor: '#091d4b', // match container
    backgroundColor: 'transparent', // match container
    style: {
      fontFamily: 'Arial, sans-serif'
    }
  },
  title: {
    text: '2025 Monthly Financial Overview',
    style: {color: '#ffffff'}
  },
  xAxis: {
    categories: months,
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      },
      rotation: -45,  // or try -45 or 45 for diagonal
    },
//    minorTicks: true,
//    minorTickInterval: 0.5,  // show tick for every month (default)
//    tickmarkPlacement: 'on',  // align ticks with category labels
    tickWidth: 1,
    title: {
        text: 'Month',
        style: {color: '#ffffff'}
    },
    crosshair: {
      color: '#5181B8',
      width: 1,
    },
    lineColor: '#ffffff',
    tickColor: '#ffffff'
  },
  yAxis: {
    title: {
      text: 'Amount (PLN)',
      style: {
        color: '#ffffff'
      }
    },
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      }
    },
    tickWidth: 0.5,
    tickColor: '#ffffff',
    lineWidth: 1,
//    gridLineColor: '#112147', // dark gray grid lines
    gridLineColor: '#303f53', // dark gray grid lines
    lineColor: '#ffffff',
//    gridLineColor: 'blue',
//    lineColor: 'blue',
    minorTickInterval: 5000,
    tickInterval: 5000,
  },
  legend: {
    itemStyle: {
      color: '#ffffff'
    }
  },
  tooltip: {
    shared: true,
    valueDecimals: 2,
    valueSuffix: ' PLN',
//    stickOnContact: false
//    backgroundColor: '#1f2937',  // dark tooltip
      backgroundColor: 'rgba(15, 23, 42, 0.6)', // dark navy with slight transparency
    style: {
//      color: '#f9fafb'
      color: '#f9fafb'
    },
    borderColor: '#ffffff',
    borderWidth: 0.1,
  },
  series: [
    { name: 'Income', data: income },
    { name: 'Expenses', data: expenses },
    { name: 'Net Savings', data: netSavings },
    { name: 'Ending Balance', data: endingBalance }
  ]
});

  Highcharts.chart('balance-chart3', {
  chart: {
    type: 'line',
    zoomType: 'xy',  // allows horizontal zooming
//    backgroundColor: '#111827', // match container
//    backgroundColor: '#0c1833', // match container
//    backgroundColor: '#091d4b', // match container
    backgroundColor: 'transparent', // match container
    style: {
      fontFamily: 'Arial, sans-serif'
    }
  },
  title: {
    text: '2025 Monthly Financial Overview',
    style: {color: '#ffffff'}
  },
  xAxis: {
    categories: months,
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      },
      rotation: -45,  // or try -45 or 45 for diagonal
    },
//    minorTicks: true,
//    minorTickInterval: 0.5,  // show tick for every month (default)
//    tickmarkPlacement: 'on',  // align ticks with category labels
    tickWidth: 1,
    title: {
        text: 'Month',
        style: {color: '#ffffff'}
    },
    crosshair: {
      color: '#5181B8',
      width: 1,
    },
    lineColor: '#ffffff',
    tickColor: '#ffffff'
  },
  yAxis: {
    title: {
      text: 'Amount (PLN)',
      style: {
        color: '#ffffff'
      }
    },
    labels: {
      style: {
        color: '#ffffff' // tailwind slate-200
      }
    },
    tickWidth: 0.5,
    tickColor: '#ffffff',
    lineWidth: 1,
//    gridLineColor: '#112147', // dark gray grid lines
    gridLineColor: '#303f53', // dark gray grid lines
    lineColor: '#ffffff',
//    gridLineColor: 'blue',
//    lineColor: 'blue',
    minorTickInterval: 5000,
    tickInterval: 5000,
  },
  legend: {
    itemStyle: {
      color: '#ffffff'
    }
  },
  tooltip: {
    shared: true,
    valueDecimals: 2,
    valueSuffix: ' PLN',
//    stickOnContact: false
//    backgroundColor: '#1f2937',  // dark tooltip
      backgroundColor: 'rgba(15, 23, 42, 0.6)', // dark navy with slight transparency
    style: {
//      color: '#f9fafb'
      color: '#f9fafb'
    },
    borderColor: '#ffffff',
    borderWidth: 0.1,
  },
  series: [
    { name: 'Income', data: income },
    { name: 'Expenses', data: expenses },
    { name: 'Net Savings', data: netSavings },
    { name: 'Ending Balance', data: endingBalance }
  ]
});

});