Deepfake Voice Detection System
A full-stack web application that uses machine learning to detect AI-generated synthetic voices with 95.93% accuracy.
Table of Contents
- Overview
- Features
- Technology Stack
- Installation
- Usage
- Project Structure
- Model Performance
- Dataset
- Screenshots
- Future Enhancements
- License
Overview
The Deepfake Voice Detection System is a Flask-based web application that distinguishes between genuine human voices and AI-generated synthetic voices. It extracts 13 acoustic features from audio files and uses ensemble machine learning models for classification.
Key Achievement: XGBoost model achieves 95.93% accuracy** on test data.
Features
- Real-time Analysis: Upload WAV/MP3 files for instant classification
- High Accuracy: 95.93% with XGBoost model
- User Management: Secure registration/login system
- History Tracking: View previous analysis results
- Confidence Scores: Probability estimates for predictions
- Responsive Design: Works on desktop and mobile

Technology Stack
Backend: Python, Flask, SQLAlchemy |
Machine Learning: XGBoost, Scikit-learn, Random Forest, SVM 
Audio Processing: Librosa, NumPy, Pandas 
Frontend: HTML5, CSS3, JavaScript, Bootstrap 
Database: SQLite 
Deployment: Local server (Flask development server) 
Installation
Prerequisites
Python 3.8 or higher
pip (Python package manager)
Step-by-Step Setup
Clone the repository
 bash
   git clone https://github.com/tazimanwar-04/deepfake-voice-detection.git
   cd deepfake-voice-detection