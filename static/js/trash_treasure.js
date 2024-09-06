document.addEventListener('DOMContentLoaded', function() {
    // Fetch and display pending points
    fetch('{{ url_for("get_pending_points") }}')
        .then(response => response.json())
        .then(data => {
            document.getElementById('pending-points-value').innerText = data.pending_points;
        });

    // Fetch and display order history
    fetch('{{ url_for("get_order_history") }}')
        .then(response => response.json())
        .then(data => {
            const historyContainer = document.getElementById('order-history-content');
            historyContainer.innerHTML = ''; // Clear any existing content

            if (data.length === 0) {
                historyContainer.innerHTML = '<p>No orders found.</p>';
            } else {
                data.forEach(order => {
                    const orderDiv = document.createElement('div');
                    orderDiv.className = 'order-item';
                    orderDiv.innerHTML = `
                        <p><strong>Name:</strong> ${order.name}</p>
                        <p><strong>Pickup Location:</strong> ${order.pickup_location}</p>
                        <p><strong>Phone:</strong> ${order.phone}</p>
                        <p><strong>Date:</strong> ${order.date}</p>
                        <p><strong>Points:</strong> ${order.points}</p>
                    `;
                    historyContainer.appendChild(orderDiv);
                });
            }
        })
        .catch(error => console.error('Error fetching order history:', error));
});
