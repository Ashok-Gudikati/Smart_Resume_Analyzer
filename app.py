from flask import Flask, render_template, request, redirect
import os
import nltk
nltk.download('punkt')
nltk.download('wordnet')

from PyPDF2 import PdfReader
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import pymysql
from courses import ds_course, web_course, android_course, ios_course, uiux_course

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

# Database connection and table creation
connection = pymysql.connect(host='localhost', user='root', password='Ashok@6300')
cursor = connection.cursor()

# Create database and table if they don't exist
cursor.execute("CREATE DATABASE IF NOT EXISTS sra;")
cursor.execute("USE sra;")
create_table_query = """
CREATE TABLE IF NOT EXISTS user_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    resume_score FLOAT NOT NULL,
    predicted_field TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
cursor.execute(create_table_query)

def extract_text(file_path):
    text = ''
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text.lower()

def preprocess_text(text):
    tokens = word_tokenize(text)
    tokens = [token for token in tokens if token.isalnum()]
    tokens = [token for token in tokens if token not in stop_words]
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    return tokens

def analyze_resume(file_path):
    resume_text = extract_text(file_path)
    tokens = preprocess_text(resume_text)

    def find_keywords(keywords):
        found_keywords = []
        for keyword in keywords:
            if keyword in tokens:
                found_keywords.append(keyword)
        return found_keywords

    suggestions = []
    roles = set()

    # Identify relevant keywords from the resume
    relevant_keywords = find_keywords(['machine learning', 'data science', 'python', 'web development', 'django', 'react', 'node', 'flask', 'android', 'kotlin', 'ios', 'swift', 'ui', 'design', 'ux', 'adobe', 'xd'])

    # Based on the identified keywords, suggest relevant courses and roles
    for keyword in relevant_keywords:
        if keyword in ['machine learning', 'data science', 'python']:
            suggestions.extend(ds_course)
            roles.add('Data Scientist')
        elif keyword in ['web development', 'django', 'react', 'node', 'flask', 'website']:
            suggestions.extend(web_course)
            roles.add('Web Developer')
        elif keyword in ['android', 'kotlin']:
            suggestions.extend(android_course)
            roles.add('Android Developer')
        elif keyword in ['ios', 'swift']:
            suggestions.extend(ios_course)
            roles.add('iOS Developer')
        elif keyword in ['ui', 'design', 'ux', 'adobe', 'xd']:
            suggestions.extend(uiux_course)
            roles.add('UI/UX Designer')

    # Score calculation based on the presence of various sections
    weights = {
        'skills': 2,
        'certifications': 1.5,
        'hobbies': 0.5,
        'projects': 2,
        'career_objective': 1,
        'keywords': 3
    }

    # Calculate individual section scores
    skills_score = weights['skills'] if 'skills' in resume_text else 0
    certifications_score = weights['certifications'] if 'certifications' in resume_text else 0
    hobbies_score = weights['hobbies'] if 'hobbies' in resume_text else 0
    projects_score = weights['projects'] if 'projects' in resume_text else 0
    career_objective_score = weights['career_objective'] if 'career objective' in resume_text else 0
    keyword_score = len(relevant_keywords) / len(['machine learning', 'data science', 'python', 'web development', 'django', 'react', 'node', 'flask', 'android', 'kotlin', 'ios', 'swift', 'ui', 'design', 'ux', 'adobe', 'xd']) * weights['keywords']

    # Overall Resume Score
    resume_score = skills_score + certifications_score + hobbies_score + projects_score + career_objective_score + keyword_score

    # Round the resume score to 2 decimal places
    resume_score = round(resume_score, 2)

    # Determine predicted field based on roles
    predicted_field = ', '.join(roles)

    # Convert suggestions list to a string for storing in the database
    recommendations_str = '\n'.join(['{}: {}'.format(course[0], course[1]) for course in suggestions])

    return resume_score, recommendations_str, predicted_field

def insert_data(name, email, resume_score, predicted_field):
    insert_query = """
    INSERT INTO user_data (name, email, resume_score, predicted_field)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(insert_query, (name, email, resume_score, predicted_field))
    connection.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        resume_score, recommendations, predicted_field = analyze_resume(file_path)
        
        name = "Test User"  # You can add a field in your form to capture the user's name
        email = "testuser@example.com"  # You can add a field in your form to capture the user's email
        
        insert_data(name, email, resume_score, predicted_field)
        
        result = {
            'email': email,
            'resume_score': resume_score,
            'career_recommendations': predicted_field,
            'resume_writing_tips': 'Add more details about your projects and skills.',
            'suggestions': recommendations.split('\n'),
            'feedback': 'Good job! Here are some suggested improvements.'
        }

        return render_template('result.html', result=result)
    return redirect('/')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['ashok']
        if username == 'admin' and password == 'admin':
            cursor.execute("SELECT * FROM user_data")
            data = cursor.fetchall()
            return render_template('admin.html', data=data)
        else:
            return "Invalid credentials"
    return render_template('admin_login.html')

if __name__ == "__main__":
    app.run(debug=True)

# Close the cursor and connection after the script ends
cursor.close()
connection.close()
