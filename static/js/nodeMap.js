document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('nodeMap').getContext('2d');
    
    fetch('/json/nodes')
        .then(response => response.json())
        .then(data => {
            let chart = new Chart(ctx, {
                type: 'bubble',
                data: {
                    datasets: [{
                        label: 'Nodes',
                        data: data,
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        x: {
                            beginAtZero: true
                        },
                        y: {
                            beginAtZero: true
                        }
                    },
                }
            });

            window.addEventListener('resize', () => {
                chart.resize();
            });
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
});