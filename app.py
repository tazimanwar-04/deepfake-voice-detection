import os
import numpy as np
import librosa
import joblib
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import json

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voice_analysis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize database
db = SQLAlchemy(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'wav', 'mp3'}

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyses = db.relationship('VoiceAnalysis', backref='owner', lazy=True)

class VoiceAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    prediction = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

# Load ML model and scaler
try:
    model = joblib.load('best_voice_model.pkl')
    scaler = joblib.load('feature_scaler.pkl')
    print("ML model and scaler loaded successfully!")
except Exception as e:
    print(f" Error loading model: {e}")
    model = None
    scaler = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_features(file_path):
    """Extract audio features"""
    try:
        y, sr = librosa.load(file_path, sr=None)
        
        duration = librosa.get_duration(y=y, sr=sr)
        zcr_mean = np.mean(librosa.feature.zero_crossing_rate(y))
        
        rmse = librosa.feature.rms(y=y)
        rmse_mean = np.mean(rmse)
        
        spec_centroid_mean = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        spec_bw_mean = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))
        
        spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        spec_contrast_mean = np.mean(spec_contrast)
        
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma)
        
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=5)
        mfccs_mean = np.mean(mfccs, axis=1)
        
        features = np.hstack([
            duration,
            zcr_mean,
            mfccs_mean,           
            spec_centroid_mean,
            spec_bw_mean,
            spec_contrast_mean,
            chroma_mean,
            rmse_mean,
            sr                  
        ])
        
        print("Features extracted successfully!")
        return features, True
        
    except Exception as e:
        print(f"xError extracting features: {e}")
        return None, False

# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

app.json_encoder = NumpyEncoder

# Session management
def login_user(user):
    session['user_id'] = user.id
    session['username'] = user.username

def logout_user():
    session.clear()

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Routes
@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check username and password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        flash('Please login to access dashboard.', 'danger')
        return redirect(url_for('login'))
        
    analyses = VoiceAnalysis.query.filter_by(user_id=user.id).order_by(VoiceAnalysis.analyzed_at.desc()).limit(10).all()
    return render_template('dashboard.html', analyses=analyses, user=user)

@app.route('/analyze', methods=['POST'])
def analyze_voice():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Please login first'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload WAV or MP3.'}), 400
    
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(file_path)
        
        print(f" File saved: {file_path}")
        
        if model is None or scaler is None:
            return jsonify({'error': 'ML model not loaded properly'}), 500
        
        # Extract features and predict
        features, success = extract_features(file_path)
        
        if not success:
            return jsonify({'error': 'Failed to process audio file'}), 400
        
        # Reshape features for scaler
        features = features.reshape(1, -1)
        features_scaled = scaler.transform(features)
        
        # Get prediction
        prediction = model.predict(features_scaled)[0]
        probability = model.predict_proba(features_scaled)[0]
        
        # Convert numpy types to Python native types for JSON serialization
        confidence = float(probability[prediction])  # Convert to Python float
        prediction_label = 'Real' if int(prediction) == 1 else 'Fake'  # Convert to Python int
        
        print(f"Prediction: {prediction_label}")
        print(f"Confidence: {confidence:.2%}")
        
        # Save to database
        analysis = VoiceAnalysis(
            user_id=user.id,
            filename=filename,
            file_path=file_path,
            prediction=prediction_label,
            confidence=confidence
        )
        db.session.add(analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'prediction': prediction_label,
            'confidence': round(confidence * 100, 2),  # Convert to percentage
            'analysis_id': analysis.id
        })
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/result/<int:analysis_id>')
def result(analysis_id):
    user = get_current_user()
    if not user:
        flash('Please login to view results.', 'danger')
        return redirect(url_for('login'))
        
    analysis = VoiceAnalysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('result.html', analysis=analysis, user=user)

# Create database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)