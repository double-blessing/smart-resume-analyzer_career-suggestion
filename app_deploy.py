import streamlit as st
import pandas as pd
import plotly.express as px
import re
import fitz  # PyMuPDF
import pdfplumber
from datetime import datetime
import tempfile
import os

# Page configuration
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .skill-tag {
        background-color: #e1f5fe;
        color: #01579b;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Skills database
SKILLS_DATABASE = {
    'Data Science': ['python', 'r', 'sql', 'machine learning', 'pandas', 'numpy', 'scikit-learn', 
                    'tensorflow', 'pytorch', 'jupyter', 'data analysis', 'statistics', 'tableau'],
    'Web Development': ['html', 'css', 'javascript', 'react', 'angular', 'vue', 'node.js', 
                       'express', 'django', 'flask', 'php', 'laravel', 'bootstrap', 'jquery'],
    'Mobile Development': ['android', 'ios', 'react native', 'flutter', 'swift', 'kotlin', 
                          'java', 'xamarin', 'ionic', 'cordova'],
    'DevOps': ['docker', 'kubernetes', 'aws', 'azure', 'jenkins', 'git', 'linux', 'bash', 
               'terraform', 'ansible'],
    'AI/ML': ['artificial intelligence', 'deep learning', 'nlp', 'computer vision', 'opencv',
              'keras', 'neural networks']
}

# Course recommendations
COURSE_RECOMMENDATIONS = {
    'Data Science': [
        'Python for Data Science - Coursera',
        'Machine Learning Course - edX',
        'Data Analysis with Pandas - Udemy',
        'Statistics for Data Science - Khan Academy'
    ],
    'Web Development': [
        'Full Stack Web Development - freeCodeCamp',
        'React Complete Guide - Udemy',
        'JavaScript Basics - Codecademy',
        'HTML/CSS Fundamentals - W3Schools'
    ],
    'Mobile Development': [
        'Android Development - Google Developers',
        'iOS Development - Apple Developer',
        'Flutter Course - Udacity',
        'React Native - Meta'
    ],
    'DevOps': [
        'Docker Essentials - Docker Hub',
        'AWS Cloud Practitioner - AWS',
        'Kubernetes Basics - CNCF',
        'Git Version Control - GitHub'
    ],
    'AI/ML': [
        'Deep Learning Specialization - Coursera',
        'Computer Vision - OpenCV',
        'Natural Language Processing - NLTK',
        'Machine Learning - Andrew Ng'
    ]
}

def extract_text_from_pdf(uploaded_file):
    """Extract text from uploaded PDF file"""
    text = ""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # Try pdfplumber first
        try:
            with pdfplumber.open(tmp_file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            # Fallback to PyMuPDF
            doc = fitz.open(tmp_file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            doc.close()
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""
    
    return text

def extract_contact_info(text):
    """Extract contact information from resume text"""
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else "Not found"
    
    # Extract phone
    phone_pattern = r'(\+?\d{1,4}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, text)
    phone = ''.join(phones[0]) if phones else "Not found"
    
    # Extract name (first meaningful line)
    lines = text.split('\n')
    name = "Not found"
    for line in lines[:10]:
        line = line.strip()
        if (len(line.split()) >= 2 and len(line) < 50 and 
            not '@' in line and not any(char.isdigit() for char in line)):
            name = line
            break
    
    return name, email, phone

def extract_skills(text):
    """Extract skills from resume text"""
    text_lower = text.lower()
    found_skills = []
    
    for field, skills in SKILLS_DATABASE.items():
        for skill in skills:
            if skill.lower() in text_lower:
                found_skills.append(skill.title())
    
    return list(set(found_skills))

def predict_career_field(skills):
    """Predict career field based on skills"""
    if not skills:
        return "General IT"
    
    field_scores = {}
    for field, field_skills in SKILLS_DATABASE.items():
        score = sum(1 for skill in skills if skill.lower() in [s.lower() for s in field_skills])
        field_scores[field] = score
    
    if not field_scores or all(score == 0 for score in field_scores.values()):
        return "General IT"
    
    # Find field with highest score
    best_field = "General IT"
    best_score = 0
    for field, score in field_scores.items():
        if score > best_score:
            best_score = score
            best_field = field
    
    return best_field

def calculate_resume_score(text, skills):
    """Calculate resume score based on various factors"""
    score = 0
    
    # Length check (appropriate resume length)
    word_count = len(text.split())
    if 200 <= word_count <= 800:
        score += 25
    elif word_count > 100:
        score += 15
    
    # Skills count
    skills_count = len(skills)
    if skills_count >= 10:
        score += 25
    elif skills_count >= 5:
        score += 20
    elif skills_count >= 1:
        score += 10
    
    # Contact information
    if '@' in text:
        score += 15
    if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', text):
        score += 10
    
    # Structure indicators
    structure_keywords = ['experience', 'education', 'skills', 'projects', 'work', 'summary']
    for keyword in structure_keywords:
        if keyword.lower() in text.lower():
            score += 4
    
    return min(int(score), 100)

def main():
    st.markdown('<h1 class="main-header">📄 Smart Resume Analyzer</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    **Welcome to Smart Resume Analyzer!** 
    
    Upload your resume in PDF format to get:
    - Instant resume scoring (0-100)
    - Career field prediction
    - Skills analysis
    - Personalized course recommendations
    - Improvement suggestions
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose your resume (PDF format)", 
        type="pdf",
        help="Upload a PDF file of your resume for analysis"
    )
    
    if uploaded_file is not None:
        with st.spinner("Analyzing your resume..."):
            # Extract text from PDF
            text = extract_text_from_pdf(uploaded_file)
            
            if text:
                # Process the resume
                name, email, phone = extract_contact_info(text)
                skills = extract_skills(text)
                predicted_field = predict_career_field(skills)
                resume_score = calculate_resume_score(text, skills)
                
                # Display results
                st.success("Analysis Complete!")
                
                # Main metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f'''
                    <div class="metric-card">
                        <h3>Resume Score</h3>
                        <h2>{resume_score}/100</h2>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f'''
                    <div class="metric-card">
                        <h3>Predicted Field</h3>
                        <h2>{predicted_field}</h2>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f'''
                    <div class="metric-card">
                        <h3>Skills Found</h3>
                        <h2>{len(skills)}</h2>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Contact Information
                st.subheader("📞 Contact Information")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Name:** {name}")
                with col2:
                    st.info(f"**Email:** {email}")
                with col3:
                    st.info(f"**Phone:** {phone}")
                
                # Skills section
                st.subheader("🛠️ Skills Identified")
                if skills:
                    skills_html = ""
                    for skill in sorted(skills):
                        skills_html += f'<span class="skill-tag">{skill}</span>'
                    st.markdown(skills_html, unsafe_allow_html=True)
                else:
                    st.warning("No specific technical skills identified. Consider adding more technical skills to your resume.")
                
                # Career recommendations
                st.subheader("🎯 Career Recommendations")
                
                if predicted_field in COURSE_RECOMMENDATIONS:
                    st.write(f"Based on your skills, **{predicted_field}** appears to be your strongest area.")
                    
                    with st.expander("📚 Recommended Learning Resources"):
                        for course in COURSE_RECOMMENDATIONS[predicted_field]:
                            st.write(f"• {course}")
                
                # Resume improvement tips
                st.subheader("💡 Resume Improvement Tips")
                
                tips = []
                if resume_score < 70:
                    tips.append("🔹 Add more relevant technical skills for your target field")
                    tips.append("🔹 Include specific achievements and quantifiable results")
                    tips.append("🔹 Ensure clear section headers (Experience, Education, Skills)")
                
                if len(skills) < 5:
                    tips.append("🔹 Add more technical skills relevant to your career field")
                
                if email == "Not found":
                    tips.append("🔹 Make sure your email address is clearly visible")
                
                if phone == "Not found":
                    tips.append("🔹 Include your phone number for easy contact")
                
                if len(text.split()) < 200:
                    tips.append("🔹 Consider adding more detail about your experience and projects")
                
                if tips:
                    for tip in tips:
                        st.write(tip)
                else:
                    st.success("🎉 Your resume looks well-structured! Keep updating it with new skills and experiences.")
                
                # Score interpretation
                st.subheader("📊 Score Breakdown")
                if resume_score >= 80:
                    st.success("Excellent! Your resume is well-optimized.")
                elif resume_score >= 60:
                    st.warning("Good resume with room for improvement.")
                else:
                    st.error("Your resume needs significant improvements.")
                
            else:
                st.error("Could not extract text from the PDF. Please ensure the file is not corrupted and contains readable text.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Smart Resume Analyzer | Perfect for 300 Level Projects | 100% Free</p>
        <p>Deploy this app for free on Streamlit Community Cloud</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()