import { chartOptions } from './charts_const.js';

export function renderCategoriesSunburstChart(containerId, data) {

Highcharts.chart(containerId, {
    chart: {
        backgroundColor: 'transparent',
    },
    title: {
        text: ''
    },
    series: [{
        type: "sunburst",
        data: data,
        allowDrillToNode: true,
//        turboThreshold: 0,
        cursor: 'pointer',
        dataLabels: {
            format: '{point.name}'
        },
        levels: [{
            level: 1,
            levelIsConstant: false,
            dataLabels: {
                rotationMode: 'parallel',
            },
        }, {
            level: 2,
            colorByPoint: true,
        }, {
            level: 3,
            colorVariation: {
                key: 'brightness',
                to: -1
            }
        }]
    }],
    exporting: { enabled: false },
    tooltip: {
        headerFormat: "",
        backgroundColor: chartOptions.colors.TOOLTIP_BG,
        style: { color: chartOptions.colors.TEXT },
        borderColor: chartOptions.colors.WHITE,
        borderWidth: chartOptions.tooltip.BORDER_WIDTH,
        pointFormat: '<b>{point.name}</b>: {point.value} transactions'
    },
});
}