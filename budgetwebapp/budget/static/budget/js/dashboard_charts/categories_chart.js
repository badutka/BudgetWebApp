import { chartOptions } from './charts_const.js';

export function renderCategoriesChart(containerId, categories, counts, amounts) {
    // Calculate cumulative percentages to find 80% cutoff
    let total = counts.reduce((a, b) => a + b, 0);
    let cumulative = 0;
    let pareto80Index = counts.findIndex(count => {
        cumulative += count;
        return (cumulative / total) * 100 >= 80;
    });

    Highcharts.chart(containerId, {
        chart: {
            backgroundColor: 'transparent',
            style: { fontFamily: chartOptions.font.FAMILY },
            animation: true
        },
        title: { text: '' },
        xAxis: {
            categories: categories,
            crosshair: true,
            labels: {
                style: { color: chartOptions.colors.WHITE },
                rotation: chartOptions.axis.LABEL_ROTATION
            },
            plotLines: [{
                value: pareto80Index,
                color: chartOptions.colors.WHITE,
                width: 2,
                dashStyle: 'ShortDash',
                label: {
                    text: '80% Pareto',
                    style: { color: chartOptions.colors.TEXT },
                    align: 'left',
                    rotation: 0
                }
            }]
        },
        yAxis: [
            {
                min: 0,
                title: {
                    text: 'Number of transactions',
                    style: { color: chartOptions.colors.WHITE }
                },
                labels: { style: { color: chartOptions.colors.WHITE } },
                tickInterval: 10,
                gridLineColor: chartOptions.colors.GRID,
                tickWidth: chartOptions.axis.TICK_WIDTH,
                tickColor: chartOptions.colors.WHITE,
                lineWidth: chartOptions.axis.LINE_WIDTH,
                lineColor: chartOptions.colors.WHITE
            },
            {
                title: {
                    text: 'Pareto %',
                    style: { color: chartOptions.colors.WHITE }
                },
                labels: { style: { color: chartOptions.colors.WHITE } },
                opposite: true,
                max: 100,
                min: 0,
                tickInterval: 10,
                gridLineColor: chartOptions.colors.GRID,
                tickWidth: chartOptions.axis.TICK_WIDTH,
                tickColor: chartOptions.colors.WHITE,
                lineWidth: chartOptions.axis.LINE_WIDTH,
                lineColor: chartOptions.colors.WHITE
            }
        ],
        tooltip: {
            shared: true,
            useHTML: true,
            backgroundColor: chartOptions.colors.TOOLTIP_BG,
            style: { color: chartOptions.colors.TEXT },
            borderColor: chartOptions.colors.WHITE,
            borderWidth: chartOptions.tooltip.BORDER_WIDTH,
            formatter: function () {
                const category = this.x;
                const columnPoint = this.points?.find(p => p.series.type === 'column');
                const paretoPoint = this.points?.find(p => p.series.type === 'pareto');
                return `
                    <b>Category: ${category}</b><br/>
                    Transactions: <b>${columnPoint?.y ?? '-'}</b><br/>
                    Pareto Count: <b>${paretoPoint ? Highcharts.numberFormat(paretoPoint.y, 2) : '-'}%</b><br/>
                `;
            }
        },
        exporting: { enabled: false },
        legend: { itemStyle: { color: chartOptions.colors.WHITE } },
        series: [
            {
                // Pareto line
                name: 'Pareto Count',
                type: 'pareto',
                baseSeries: 1,
                yAxis: 1, // secondary
                zIndex: 10
            },
            {
                // Column for transactions
                name: 'Parent Categories Transactions',
                type: 'column',
                data: counts,
                yAxis: 0, // primary
                zIndex: 2,
                dataLabels: {
                    enabled: true,
                    color: chartOptions.colors.WHITE
                }
            }
        ]
    });
}