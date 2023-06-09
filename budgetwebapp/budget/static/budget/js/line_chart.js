const plugin = {
    id: 'customCanvasBackgroundColor',
    beforeDraw: (chart, args, options) => {
        const {ctx} = chart;
        ctx.save();
        ctx.globalCompositeOperation = 'destination-over';
        ctx.fillStyle = options.color || '#99ffff';
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
    }
};

customOptions = {
    responsive: true,
    scales: {
        y: {
            beginAtZero: true,
            ticks: {
                callback: function(value, index, values) {
                    return value.toLocaleString(); // Format y-axis labels with thousand separators
                },
                color: '#fff' // Set font color of y-axis labels to white
            }
        },
        x: {
            ticks: {
                color: '#fff' // Set font color of x-axis labels to white
            }
        }
    },
    plugins: {
        customCanvasBackgroundColor: {
            color: '#2c2c2c',
        },
        title: {
            display: true,
            text: 'Summary Line Graph',
            font: {
                weight: 'bold',
            },
            color: '#fff', // Set font color of title to white
        },
        legend: {
            position: 'bottom',
            labels: {
            color: '#fff' // Set font color of legend labels to white
            }
        }
    },
    tooltips: {
        mode: 'index',
        intersect: false,
        callbacks: {
            label: function(context) {
                var label = context.dataset.label || '';
                if (label) {
                    label += ': ';
                }
                label += context.formattedValue.toLocaleString(); // Format tooltip values with thousand separators
                return label;
            }
        },
        backgroundColor: 'rgba(0, 0, 0, 0.8)', // Set tooltip background color to dark
        titleFontColor: '#fff', // Set font color of tooltip title to white
        bodyFontColor: '#fff' // Set font color of tooltip body to white
    },
    hover: {
        mode: 'nearest',
        intersect: true
    }
}

document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/chart-data/')
        .then(response => response.json())
        .then(data => {
            // Retrieve the data from the API response
            var labels = data.labels;
            var expensesData = data.expenses_data;
            var incomeData = data.income_data;
            var balanceData = data.balance_data;
    
    data = {
        labels: labels,
        datasets: [{
            label: 'Expenses',
            data: expensesData,
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            fill: true,
            tension: 0.1
        }, {
            label: 'Income',
            data: incomeData,
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            fill: true,
            tension: 0.1
        }, {
            label: 'Ending Balance',
            data: balanceData,
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            fill: true,
            tension: 0.1
        }]
    }

    // Create the line graph
    var ctx = document.getElementById('lineGraph').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: data,
        options: customOptions,
        plugins: [plugin],
    });

    }).catch(error => {console.error('Error:', error);});
});