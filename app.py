from flask import Flask, request, redirect, url_for, render_template,jsonify,send_from_directory
import subprocess
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from chatbot import chatbot_response

from flask import Flask, render_template, request, redirect, url_for
import os
import numpy as np
import cv2
import torch
from torchvision import models, transforms
from PIL import Image

import os
import json
import random
import ssl
from werkzeug.utils import secure_filename
from PIL import Image
import os
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.inception_v3 import preprocess_input
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import nltk
import sqlite3

from models import db, Post, Comment, Like


app = Flask(__name__)

model = models.detection.maskrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Define the image transforms
transform = transforms.Compose([
    transforms.ToTensor()
])

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///community.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'



# Initialize db with the app (only once)
db.init_app(app)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/volunteer')
def volunteer():
    return render_template('volunteer.html')

@app.route('/static/plots/<path:filename>')
def serve_plot(filename):
    return send_from_directory('static/plots', filename)

@app.route('/generate-plots')
def generate_plots():
    # Call the script to generate plots
    subprocess.run(['python', 'generate_plots.py'], check=True)
    return "Plots generated successfully!"

# Initialize the database
def init_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS complaints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        complaint_data TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# Route to display the form and handle form submission
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    if request.method == 'POST':
        # Collect form data
        recipient_name = request.form['recipient_name']
        specific_issue = request.form['specific_issue']
        location = request.form['location']
        duration = request.form['duration']
        issue_details = request.form['issue_details']
        full_name = request.form['full_name']
        address = request.form['address']
        contact_info = request.form['contact_info']
        email_address = request.form['email_address']
        
        # Combine all data into a single string
        complaint_data = f"Issue: {specific_issue}, Location: {location}, Duration: {duration}, Details: {issue_details}"

        # Store the data in the database
        conn = sqlite3.connect('complaints.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO complaints (complaint_data) VALUES (?)''', (complaint_data,))
        conn.commit()
        conn.close()

        return redirect(url_for('voice'))
    
    return render_template('voice.html')


# Route to handle form submission
@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    # Collect form data
    recipient_name = request.form['recipient_name']
    specific_issue = request.form['specific_issue']
    location = request.form['location']
    duration = request.form['duration']
    issue_details = request.form['issue_details']
    full_name = request.form['full_name']
    address = request.form['address']
    contact_info = request.form['contact_info']
    email_address = request.form['email_address']
    
    # Combine all data into a single string
    complaint_data = f"Issue: {specific_issue}, Location: {location}, Duration: {duration}, Details: {issue_details}"

    # Store the data in the database
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO complaints (complaint_data) VALUES (?)''', (complaint_data,))
    conn.commit()
    conn.close()

    return redirect(url_for('voice'))


# Define class points
@app.route('/submit', methods=['POST'])
def submit_categories():
    points = {
        'biological': 10,
        'plastic': 5,
        'paper': 7,
        'clothes': 8,
        'electronics': 12
    }
    
    # Calculate total points
    total_points = 0
    categories = request.form.getlist('categories')
    
    for category in categories:
        total_points += points.get(category, 0)

    return render_template('trash_treasure.html', 
                           total_points=total_points, 
                           filename=request.form.get('filename'), 
                           output_path=url_for('static', filename=f'output/{request.form.get("filename")}'),
                           mask_paths=request.form.getlist('mask_paths'))
# Initialize SQLite database
def initialize_db():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            pickup_location TEXT NOT NULL,
            total_points INTEGER NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def apply_mask_rcnn_with_bboxes(image_path, output_path):
    # Load image
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0)  # Add batch dimension

    # Get model predictions
    with torch.no_grad():
        predictions = model(image_tensor)

    # Process predictions
    masks = predictions[0]['masks'].cpu().numpy()
    scores = predictions[0]['scores'].cpu().numpy()
    boxes = predictions[0]['boxes'].cpu().numpy()

    # Load original image as OpenCV format
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    mask_images = []
    mask_paths = []

    # Create an output image with refined masks and bounding boxes
    for i in range(masks.shape[0]):
        if scores[i] > 0.5:  # Filter by confidence score
            mask = masks[i, 0] > 0.5
            mask = mask.astype(np.uint8)  # Convert boolean mask to uint8

            # Apply morphological operations to refine mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Close small holes
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # Remove small objects

            # Extract the masked area from the original image
            mask_color = np.zeros_like(img_cv)
            mask_color[mask > 0] = img_cv[mask > 0]
            
            # Save each mask segment separately
            mask_filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_mask_{i}.jpg"
            mask_output_path = os.path.join(app.root_path, 'static', 'masks', mask_filename)
            cv2.imwrite(mask_output_path, mask_color)
            mask_paths.append(url_for('static', filename=f'masks/{mask_filename}'))

            # Combine mask with the original image for visualization
            color_mask = np.zeros_like(img_cv)
            color_mask[mask > 0] = [0, 255, 0]  # Green mask for visualization
            img_cv = cv2.addWeighted(img_cv, 1.0, color_mask, 0.5, 0)

            # Draw bounding box
            x_min, y_min, x_max, y_max = boxes[i].astype(int)
            cv2.rectangle(img_cv, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)  # Red bounding box

            # Optionally, add label text
            label = f"Score: {scores[i]:.2f}"
            cv2.putText(img_cv, label, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Save the processed image
    cv2.imwrite(output_path, img_cv)

    return mask_paths

@app.route('/submit_details', methods=['POST'])
def submit_details():
    name = request.form.get('name')
    phone = request.form.get('phone')
    pickup_location = request.form.get('pickup_location')
    total_points = request.form.get('total_points')

    # Save details to SQLite database
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO user_details (name, phone, pickup_location, total_points)
        VALUES (?, ?, ?, ?)
    ''', (name, phone, pickup_location, total_points))

    conn.commit()
    conn.close()

    # Render confirmation page
    return render_template('confirmation.html', name=name, phone=phone, pickup_location=pickup_location, total_points=total_points)

@app.route('/upload_masks', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file:
            # Save uploaded file
            filename = file.filename
            input_path = os.path.join(app.root_path, 'uploads', filename)
            os.makedirs(os.path.dirname(input_path), exist_ok=True)
            file.save(input_path)

            # Define output paths
            output_path = os.path.join(app.root_path, 'static', 'output', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Apply Mask R-CNN and save outputs
            mask_paths = apply_mask_rcnn_with_bboxes(input_path, output_path)

            return render_template('trash_treasure.html', filename=filename, output_path=url_for('static', filename=f'output/{filename}'), mask_paths=mask_paths)

    return render_template('trash_treasure.html')

@app.route('/get_pending_points')
def get_pending_points():
    # Fetch total points from the database
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(total_points) FROM user_details')
    result = cursor.fetchone()[0] or 0
    conn.close()
    
    return jsonify({'pending_points': result})

@app.route('/get_order_history')
def get_order_history():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, pickup_location, phone, total_points FROM user_details')
    orders = cursor.fetchall()
    conn.close()

    # Convert to a list of dictionaries
    orders_list = [{'name': order[0], 'pickup_location': order[1], 'phone': order[2], 'total_points': order[3]} for order in orders]
    
    return jsonify(orders_list)

@app.route('/trash_treasure')
def trash_treasure():
    return render_template('trash_treasure.html')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# db = SQLAlchemy(app)

@app.route('/community', methods=['GET', 'POST'])
def community():
    if request.method == 'POST':
        # Handle post upload
        caption = request.form.get('caption')
        image = request.files['image']
        if image:
            filename = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_post = Post(image_filename=filename, caption=caption)
            db.session.add(new_post)
            db.session.commit()
        return redirect(url_for('community'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('community.html', posts=posts)

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    content = request.form.get('content')
    if content:
        new_comment = Comment(post_id=post_id, content=content)
        db.session.add(new_comment)
        db.session.commit()
        # Return the new comment data in JSON format
        return jsonify({'content': new_comment.content})
    return jsonify({'error': 'No content provided'}), 400

@app.route('/like/<int:post_id>', methods=['POST'])
def like(post_id):
    new_like = Like(post_id=post_id)
    db.session.add(new_like)
    db.session.commit()
    
    # Get the updated like count for the post
    like_count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'likes': like_count})

@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return '', 204

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    user_message = data.get('message', '')
    response = chatbot_response(user_message)  # Ensure chatbot() returns a response
    return jsonify({'response': response})

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    password = request.form.get('password')
    
    new_user = User(name=name, phone=phone, email=email, password=password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return render_template('index.html', success_message=f"Signup successful! Welcome, {name}.")
    except IntegrityError:
        db.session.rollback()
        return render_template('index.html', error_message="User already exists!")

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email, password=password).first()
    
    if user:
        return render_template('index.html', success_message=f"Login successful! Welcome back, {user.name}.")
    else:
        return render_template('index.html', login_error_message="No user found with these credentials.")
    

if __name__ == '__main__':
    initialize_db()
    init_db()  # Initialize the database
    app.run(debug=True)
