from flask import Flask, request, redirect, url_for, render_template,jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from chatbot import chatbot_response

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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///community.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'



# Initialize db with the app (only once)
db.init_app(app)

# Load the model
model = tf.keras.models.load_model('models/waste_classifier_inceptionv3_custom.h5')

# Define class points
class_points = {
    'battery': 50,
    'biological': 3,
    'cardboard': 10,
    'clothes': 25,
    'glass': 30,
    'metal': 20,
    'paper': 10,
    'plastic': 5,
    'shoes': 20,
    'trash': 1
}
# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('pickup_requests.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            pickup_location TEXT,
            date TEXT,
            points INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Define image processing function
def load_and_preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, 0)
    img_array = preprocess_input(img_array)
    return img_array

@app.route('/get_points', methods=['GET'])
def get_points():
    conn = sqlite3.connect('pickup_requests.db')
    cursor = conn.cursor()
    
    # Fetch sum of all points from the database
    cursor.execute('SELECT SUM(points) FROM requests')
    pending_points = cursor.fetchone()[0] or 0  # Default to 0 if no points
    
    conn.close()
    
    return jsonify({'pendingPoints': pending_points, 'confirmedPoints': 0})

@app.route('/get_order_history', methods=['GET'])
def get_order_history():
    conn = sqlite3.connect('pickup_requests.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, pickup_location, phone, date, points FROM requests")
    orders = cursor.fetchall()
    conn.close()
    
    order_list = [{'name': row[0], 'pickupLocation': row[1], 'phone': row[2], 'date': row[3], 'points': row[4]} for row in orders]
    
    return jsonify({'orders': order_list})
    


@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    filename = secure_filename(file.filename)
    file_path = os.path.join('static/uploads', filename)
    file.save(file_path)

    # Load and preprocess the image
    img_array = load_and_preprocess_image(file_path)
    predictions = model.predict(img_array)
    class_names = ['battery', 'biological', 'cardboard', 'clothes', 'glass', 'metal', 'paper', 'plastic', 'shoes', 'trash']
    predicted_class_index = np.argmax(predictions[0])
    predicted_class_name = class_names[predicted_class_index]
    points = class_points.get(predicted_class_name, 0)

    # Return the points for the processed image
    return jsonify({'points': points})

@app.route('/submit_pickup', methods=['POST'])
def submit_pickup():
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    pickup_location = data.get('pickupLocation')
    date = data.get('date')
    points = data.get('points')

    conn = sqlite3.connect('pickup_requests.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests (name, phone, pickup_location, date, points)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, phone, pickup_location, date, points))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Pickup request submitted successfully'})

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
    init_db()
    app.run(debug=True)
