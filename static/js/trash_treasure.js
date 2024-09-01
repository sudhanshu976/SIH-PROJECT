$(document).ready(function () {
    let totalPoints = 0;

    // Handle file upload and points calculation
    $('#imageUpload').on('change', function (event) {
        let files = event.target.files;
        $('#imagePreview').empty();
        let pointsArray = [];

        for (let i = 0; i < files.length; i++) {
            let file = files[i];
            let reader = new FileReader();

            reader.onload = function (e) {
                let img = $('<img>').attr('src', e.target.result);
                $('#imagePreview').append(img);
                processImage(file, i, files.length);
            };
            reader.readAsDataURL(file);
        }

        function processImage(file, index, totalFiles) {
            let formData = new FormData();
            formData.append('image', file);

            $.ajax({
                url: '/process_image',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function (response) {
                    let points = response.points;
                    pointsArray.push(points);
                    totalPoints += points;

                    if (pointsArray.length === totalFiles) {
                        $('#totalPoints').text(`Total Points: ${totalPoints}`);
                        $('#points').val(totalPoints);
                    }
                },
                error: function () {
                    console.log('Error processing image');
                }
            });
        }
    });

    // Show the popup form when the submit button is clicked
    $('#submitButton').on('click', function () {
        console.log('Submit button clicked'); // Debugging line
        $('#popupForm').fadeIn();
    });

    // Close the popup form
    $('.close-btn').on('click', function () {
        $('#popupForm').fadeOut();
    });

    // Submit form data to backend
    $('#pickupForm').on('submit', function (e) {
        e.preventDefault();

        let formData = {
            name: $('#name').val(),
            phone: $('#phone').val(),
            pickupLocation: $('#pickupLocation').val(),
            date: $('#date').val(),
            points: $('#points').val()
        };

        $.ajax({
            url: '/submit_pickup',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function (response) {
                alert('Pickup request submitted successfully!');
                $('#popupForm').fadeOut();
                $('#pickupForm')[0].reset();
                $('#totalPoints').text('Total Points: 0');
                totalPoints = 0;
            },
            error: function () {
                alert('Error submitting pickup request');
            }
        });
    });

    // Fetch points and order history when the page loads
    fetchPoints();
    fetchOrderHistory();

    // Function to fetch points from the backend
    function fetchPoints() {
        $.ajax({
            url: '/get_points',
            method: 'GET',
            success: function (response) {
                $('#pendingPoints').text(response.pendingPoints);
                $('#confirmedPoints').text(response.confirmedPoints);
            },
            error: function (error) {
                console.error('Error fetching points:', error);
            }
        });
    }

    // Function to fetch order history from the backend
    function fetchOrderHistory() {
        $.ajax({
            url: '/get_order_history',
            method: 'GET',
            success: function (response) {
                let orderList = $('#orderList');
                orderList.empty();
                if (response.orders && response.orders.length > 0) {
                    response.orders.forEach(function (order) {
                        let orderItem = `
                            <div class="order-item">
                                <div><strong>Name:</strong> ${order.name}</div>
                                <div><strong>Pickup Location:</strong> ${order.pickupLocation}</div>
                                <div><strong>Phone Number:</strong> ${order.phone}</div>
                                <div><strong>Date:</strong> ${order.date}</div>
                                <div><strong>Points:</strong> ${order.points}</div>
                            </div>
                        `;
                        orderList.append(orderItem);
                    });
                } else {
                    orderList.append('<p>No orders found.</p>');
                }
            },
            error: function (error) {
                console.error('Error fetching order history:', error);
                $('#orderList').append('<p>Error fetching order history.</p>');
            }
        });
    }
});
