function renderChartInModal() {
const chartData = JSON.parse(document.getElementById('chart-data').textContent);

Highcharts.chart('t9ns-basic-stats-on-modal', {
  chart: {
    type: 'scatter',
    spacingTop: 10,
    spacingBottom: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.07)'
  },
  title: { text: '' },
  legend: { enabled: false },
  xAxis: {
    tickInterval: 1,
    gridLineWidth: 1,
    title: { text: '' },
    gridLineColor: 'rgba(255, 255, 255, 0.5)',
    labels: {style: { color: 'rgba(255, 255, 255, 0.9)' }},
    tickColor: 'rgba(255, 255, 255, 0.5)',
    lineColor: 'rgba(255, 255, 255, 0.5)',
    gridLineWidth: 0
  },
  yAxis: {
    min: -0.5,
    max: 0.5,
    visible: false,
    gridLineWidth: 0,
    labels: { enabled: false },
    title: { text: '' },
  },
  tooltip: {
    formatter: function () {
      return this.point.name + ': ' + this.x + ' PLN';
    }
  },
  exporting: {
    enabled: false,
    fallbackToExportServer: false
  },
  series: [{
    data: chartData,
    marker: { radius: 4, fillColor: '#1abc9c'},
    dataLabels: {
      enabled: true,
      align: 'left',
      verticalAlign: 'bottom',
      x: 5,
      y: 0,
      style: { fontSize: '12px', fontWeight: 'bold', color: 'white' },
      formatter: function() {
        return this.point.name;
      }
    }
  }]
});
}