import streamlit as st
import google.generativeai as genai
import re
import time
import json
import os
import pandas as pd
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configure page
st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    page_icon="👨‍💻",
    layout="wide"
)

# Apply custom styling
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .st-emotion-cache-16txtl3 h1 {
        font-weight: 600;
        color: #2e6fdf;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {
        "name": None,
        "email": None,
        "phone": None,
        "experience": None,
        "desired_position": None,
        "location": None,
        "tech_stack": [],
        "answers": [],
        "questions": [],
        "grade": None
    }
if "current_state" not in st.session_state:
    st.session_state.current_state = "greeting"
if "current_tech" not in st.session_state:
    st.session_state.current_tech = None
if "current_tech_index" not in st.session_state:
    st.session_state.current_tech_index = 0
if "questions_asked" not in st.session_state:
    st.session_state.questions_asked = 0
if "sentiment_score" not in st.session_state:
    st.session_state.sentiment_score = 0
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "all_candidates" not in st.session_state:
    st.session_state.all_candidates = []

# Configure Gemini AI
def configure_genai():
    genai.configure(api_key=API_KEY)
    return genai.GenerativeModel('gemini-2.0-flash-lite')

# Validation functions
def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r'^\+?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

# Sentiment analysis function
def analyze_sentiment(text):
    positive_words = [
        'happy', 'great', 'good', 'excellent', 'thank', 'appreciate', 'excited',
        'love', 'enjoy', 'passionate', 'interested', 'eager', 'enthusiastic', 
        'delighted', 'pleased', 'satisfied', 'helpful', 'positive', 'wonderful',
        'fantastic', 'amazing', 'awesome', 'impressive', 'brilliant', 'valuable',
        'confident', 'skilled', 'capable', 'successful', 'experienced', 'effective'
    ]
    
    negative_words = [
        'bad', 'poor', 'frustrated', 'annoyed', 'difficult', 'problem', 'issue',
        'hate', 'dislike', 'boring', 'confused', 'challenging', 'hard', 'worry',
        'concerned', 'trouble', 'disappointed', 'negative', 'terrible', 'horrible',
        'awful', 'unfortunate', 'struggle', 'complicated', 'uncertain', 'doubt',
        'lacking', 'insufficient', 'ineffective', 'dissatisfied', 'unfamiliar'
    ]
    
    text = text.lower()
    sentiment = 0
    
    for word in positive_words:
        if word in text:
            sentiment += 1
    
    for word in negative_words:
        if word in text:
            sentiment -= 1
            
    return sentiment

# Grade candidate automatically using Gemini
def grade_candidate(model, candidate_info):
    prompt = f"""
    Please evaluate this tech candidate on a scale of 1-10 based on the following information:
    
    Name: {candidate_info.get('name', 'Unknown')}
    Experience: {candidate_info.get('experience', 'N/A')}
    Desired Position: {candidate_info.get('desired_position', 'N/A')}
    Tech Stack: {', '.join(candidate_info.get('tech_stack', []))}
    Sentiment Score: {candidate_info.get('sentiment_score', 0)}
    
    Technical Q&A:
    """
    
    # Add Q&A pairs
    for q, a in zip(candidate_info.get('questions', []), candidate_info.get('answers', [])):
        prompt += f"\nQ: {q}\nA: {a}\n"
    
    prompt += """
    Return ONLY a single number from 1-10 representing their suitability for the role, where:
    1-3: Not suitable
    4-6: Average candidate
    7-8: Good candidate
    9-10: Excellent candidate
    
    Consider their experience level, technical knowledge depth, communication skills indicated in their answers, 
    and alignment of their tech stack with their desired position.
    
    Return only a number with no additional text.
    """
    
    response = model.generate_content(prompt)
    try:
        # Extract just the number from the response
        grade = int(re.search(r'\d+', response.text).group())
        # Ensure it's in range 1-10
        return max(1, min(10, grade))
    except:
        # Default to 5 if parsing fails
        return 5

# Check for exit keywords
def check_exit(text):
    exit_keywords = ['exit', 'quit', 'goodbye', 'bye', 'end', 'stop']
    return any(keyword in text.lower() for keyword in exit_keywords)

# System prompt for assistant
def create_system_prompt():
    return f"""
    You are a hiring assistant chatbot for TalentScout, a recruitment agency specializing in technology placements.
    Your name is TalentScout Assistant.
    Your primary tasks are:
    1. Collect candidate information (name, email, phone, experience, desired position, location, tech stack)
    2. Ask relevant technical questions based on their declared tech stack
    3. Maintain a professional and friendly tone throughout the conversation
    
    Current candidate information: {json.dumps(st.session_state.candidate_info, indent=2)}
    Current state: {st.session_state.current_state}
    
    Rules:
    - Keep responses concise and professional.
    - Focus on collecting required information in a conversational manner.
    - Generate one technical question at a time and analyze the answer before asking follow-up questions.
    - the answer of the question should be short (1 - 2 lines maximum).
    - Do not hallucinate or make up information about the candidate.
    - Do not deviate from the purpose of candidate screening.
    - If the candidate wants to end the conversation, thank them and close politely.
    """

# Generate a single tech question
def generate_tech_question(model, tech, previous_answer=None, question_number=1):
    if previous_answer:
        prompt = f"""
        Based on the candidate's previous answer: "{previous_answer}" 
        to a question about {tech}, generate a follow-up technical question to further assess their knowledge.
        The question should be related to their previous answer but explore a different aspect or go deeper into the topic.
        the answer of the question should be short (few words or 1 - 2 lines maximum).
        Return only the question itself with no additional text.
        """
    else:
        prompt = f"""
        Generate a single technical interview question to assess a candidate's proficiency in {tech}.
        This is question #{question_number} about {tech}.
        The question should require critical thinking and not be a simple definition or trivia.
        the answer of the question should be short (few words or 1 - 2 lines maximum).
        Return only the question itself with no additional text.
        """
    
    response = model.generate_content(prompt)
    return response.text.strip()

# Analyze candidate's answer
def analyze_answer(model, tech, question, answer):
    prompt = f"""
    Analyze this candidate's answer about {tech}:
    
    Question: {question}
    Answer: {answer}
    
    Provide a brief assessment of the answer's technical accuracy and depth of knowledge. 
    Consider factors like:
    - Technical correctness
    - Depth of understanding
    - Practical experience indicated
    
    Keep your analysis brief (2-3 sentences max).
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

# # Generate PDF report
# def generate_pdf_report():
#     doc = SimpleDocTemplate("candidates_report.pdf", pagesize=letter)
#     styles = getSampleStyleSheet()
#     elements = []
    
#     # Title
#     title = Paragraph(f"TalentScout Candidates Report - {datetime.now().strftime('%Y-%m-%d')}", styles["Heading1"])
#     elements.append(title)
#     elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    
#     # Loop through all candidates
#     for idx, candidate in enumerate(st.session_state.all_candidates):
#         # Candidate header
#         name = candidate.get("name", "Unknown")
#         elements.append(Paragraph(f"Candidate #{idx+1}: {name}", styles["Heading2"]))
        
#         # Basic info table
#         basic_data = [
#             ["Email", candidate.get("email", "N/A")],
#             ["Phone", candidate.get("phone", "N/A")],
#             ["Experience", candidate.get("experience", "N/A")],
#             ["Position", candidate.get("desired_position", "N/A")],
#             ["Location", candidate.get("location", "N/A")],
#             ["Tech Stack", ", ".join(candidate.get("tech_stack", []))],
#             ["Sentiment Score", str(candidate.get("sentiment_score", 0))],
#             ["AI Grade", f"{candidate.get('grade', 'Not graded')}/10"]
#         ]
        
#         # Create the table
#         basic_table = Table(basic_data, colWidths=[100, 400])
#         basic_table.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
#             ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
#             ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
#             ('GRID', (0, 0), (-1, -1), 1, colors.black)
#         ]))
#         elements.append(basic_table)
        
#         # # Q&A section if available
#         # if "questions" in candidate and "answers" in candidate:
#         #     elements.append(Paragraph("<br/>Technical Assessment:", styles["Heading3"]))
            
#         #     qa_data = [["Question", "Answer"]]
#         #     for q, a in zip(candidate.get("questions", []), candidate.get("answers", [])):
#         #         qa_data.append([q, a])
            
#         #     if len(qa_data) > 1:  # If there are any Q&As
#         #         qa_table = Table(qa_data, colWidths=[250, 250])
#         #         qa_table.setStyle(TableStyle([
#         #             ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
#         #             ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
#         #             ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         #             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         #             ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
#         #             ('GRID', (0, 0), (-1, -1), 1, colors.black)
#         #         ]))
#         #         elements.append(qa_table)
        
#         # elements.append(Paragraph("<br/><br/>", styles["Normal"]))

#         # Q&A section if available
#         if "questions" in candidate and "answers" in candidate:
#             elements.append(Paragraph("<br/>Technical Assessment:", styles["Heading3"]))
            
#             # Create paragraph style for table cells that will wrap text properly
#             cell_style = styles["Normal"]
#             cell_style.wordWrap = 'CJK'  # This enables better word wrapping
            
#             # Create the data with paragraphs instead of raw text
#             qa_data = [["Question", "Answer"]]
#             for q, a in zip(candidate.get("questions", []), candidate.get("answers", [])):
#                 # Convert q and a to Paragraph objects for better text handling
#                 q_para = Paragraph(q, cell_style)
#                 a_para = Paragraph(a, cell_style)
#                 qa_data.append([q_para, a_para])
            
#             if len(qa_data) > 1:  # If there are any Q&As
#                 # Make the table with auto row heights
#                 qa_table = Table(qa_data, colWidths=[250, 250])
#                 qa_table.setStyle(TableStyle([
#                     ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
#                     ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
#                     ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#                     ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to top of cell
#                     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#                     ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
#                     ('TOPPADDING', (0, 0), (-1, -1), 6),  # Add padding at top
#                     ('GRID', (0, 0), (-1, -1), 1, colors.black)
#                 ]))
#                 elements.append(qa_table)

#         elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    
#     # Build the PDF
#     doc.build(elements)
#     return "candidates_report.pdf"


# Update the generate_pdf_report function to include sentiment classification
def generate_pdf_report():
    doc = SimpleDocTemplate("candidates_report.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title = Paragraph(f"TalentScout Candidates Report - {datetime.now().strftime('%Y-%m-%d')}", styles["Heading1"])
    elements.append(title)
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    
    # Loop through all candidates
    for idx, candidate in enumerate(st.session_state.all_candidates):
        # Candidate header
        name = candidate.get("name", "Unknown")
        elements.append(Paragraph(f"Candidate #{idx+1}: {name}", styles["Heading2"]))
        
        # Get sentiment score and determine classification
        sentiment = candidate.get("sentiment_score", 0)
        sentiment_class = "Neutral"
        if sentiment > 3:
            sentiment_class = "Very Positive"
        elif sentiment > 0:
            sentiment_class = "Positive"
        elif sentiment < 0:
            sentiment_class = "Negative"
        
        # Basic info table with sentiment classification
        basic_data = [
            ["Email", candidate.get("email", "N/A")],
            ["Phone", candidate.get("phone", "N/A")],
            ["Experience", candidate.get("experience", "N/A")],
            ["Position", candidate.get("desired_position", "N/A")],
            ["Location", candidate.get("location", "N/A")],
            ["Tech Stack", ", ".join(candidate.get("tech_stack", []))],
            ["Sentiment Score", f"{sentiment} ({sentiment_class})"],
            ["AI Grade", f"{candidate.get('grade', 'Not graded')}/10"]
        ]
        
        # Create the table
        basic_table = Table(basic_data, colWidths=[100, 400])
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(basic_table)
        
        # Q&A section if available
        if "questions" in candidate and "answers" in candidate:
            elements.append(Paragraph("<br/>Technical Assessment:", styles["Heading3"]))
            
            # Create paragraph style for table cells that will wrap text properly
            cell_style = styles["Normal"]
            cell_style.wordWrap = 'CJK'  # This enables better word wrapping
            
            # Create the data with paragraphs instead of raw text
            qa_data = [["Question", "Answer"]]
            for q, a in zip(candidate.get("questions", []), candidate.get("answers", [])):
                # Convert q and a to Paragraph objects for better text handling
                q_para = Paragraph(q, cell_style)
                a_para = Paragraph(a, cell_style)
                qa_data.append([q_para, a_para])
            
            if len(qa_data) > 1:  # If there are any Q&As
                # Make the table with auto row heights
                qa_table = Table(qa_data, colWidths=[250, 250])
                qa_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to top of cell
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),  # Add padding at top
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(qa_table)

        elements.append(Paragraph("<br/><br/>", styles["Normal"]))
    
    # Build the PDF
    doc.build(elements)
    return "candidates_report.pdf"

# Process user input
def process_user_input(model, user_input):
    current_state = st.session_state.current_state
    candidate_info = st.session_state.candidate_info
    
    # Check for exit request
    if check_exit(user_input):
        # Save the candidate before exiting if they've provided at least a name
        if candidate_info["name"]:
            # Add sentiment score to the candidate info
            candidate_info["sentiment_score"] = st.session_state.sentiment_score
            
            # Grade the candidate
            candidate_info["grade"] = grade_candidate(model, candidate_info)
            
            # Create a copy to avoid reference issues
            st.session_state.all_candidates.append(candidate_info.copy())
        
        st.session_state.current_state = "farewell"
        return "Thank you for your time! Your information has been recorded. A TalentScout recruiter will contact you soon if your profile matches our open positions. Have a great day!"
    
    # Analyze sentiment
    sentiment = analyze_sentiment(user_input)
    st.session_state.sentiment_score += sentiment
    
    # State machine for conversation flow
    if current_state == "greeting":
        st.session_state.current_state = "ask_name"
        return "Welcome to TalentScout! I'm your hiring assistant, and I'll help with the initial screening process. Could you please tell me your full name?"
    
    elif current_state == "ask_name":
        candidate_info["name"] = user_input
        st.session_state.current_state = "ask_email"
        return f"Nice to meet you, {user_input}! Could you please provide your email address so we can contact you?"
    
    elif current_state == "ask_email":
        if validate_email(user_input):
            candidate_info["email"] = user_input
            st.session_state.current_state = "ask_phone"
            return "Thank you! Now, could you share your phone number?"
        else:
            return "That doesn't appear to be a valid email address. Could you please provide a valid email?"
    
    elif current_state == "ask_phone":
        if validate_phone(user_input):
            candidate_info["phone"] = user_input
            st.session_state.current_state = "ask_experience"
            return "Great! How many years of professional experience do you have in the tech industry?"
        else:
            return "That doesn't appear to be a valid phone number. Please provide a valid phone number with 10-15 digits."
    
    elif current_state == "ask_experience":
        candidate_info["experience"] = user_input
        st.session_state.current_state = "ask_position"
        return "Thank you for sharing your experience. What position(s) are you interested in applying for?"
    
    elif current_state == "ask_position":
        candidate_info["desired_position"] = user_input
        st.session_state.current_state = "ask_location"
        return "Got it! Could you please tell me your current location or the location where you're seeking employment?"
    
    elif current_state == "ask_location":
        candidate_info["location"] = user_input
        st.session_state.current_state = "ask_tech_stack"
        return "Thank you! Now, please list the technologies you're proficient in (programming languages, frameworks, databases, tools, etc.). Separate each with a comma."
    
    elif current_state == "ask_tech_stack":
        tech_stack = [tech.strip() for tech in user_input.split(',')]
        candidate_info["tech_stack"] = tech_stack
        
        st.session_state.current_state = "tech_questions"
        st.session_state.current_tech_index = 0
        st.session_state.questions_asked = 0
        
        if tech_stack:
            st.session_state.current_tech = tech_stack[0]
            # Generate first question
            first_question = generate_tech_question(model, st.session_state.current_tech)
            candidate_info["questions"].append(first_question)
            return f"Great! Let's assess your knowledge of {st.session_state.current_tech}. {first_question}"
        else:
            st.session_state.current_state = "farewell"
            return "I notice you didn't specify any technologies. Unfortunately, we need this information to proceed. Would you like to try again and list your technical skills?"
    
    elif current_state == "tech_questions":
        # Store the answer
        candidate_info["answers"].append(user_input)
        
        # Analyze the answer (this won't be shown to the candidate but will be stored)
        current_question = candidate_info["questions"][-1]
        analysis = analyze_answer(model, st.session_state.current_tech, current_question, user_input)
        
        st.session_state.questions_asked += 1
        
        # Ask a follow-up question for the current tech or move to the next tech
        if st.session_state.questions_asked < 2:  # Limit to 2 questions per tech
            # Generate a follow-up question based on the previous answer
            follow_up = generate_tech_question(
                model, 
                st.session_state.current_tech, 
                previous_answer=user_input,
                question_number=st.session_state.questions_asked + 1
            )
            candidate_info["questions"].append(follow_up)
            return f"Thank you for your response. {follow_up}"
        else:
            # Move to the next technology
            st.session_state.current_tech_index += 1
            st.session_state.questions_asked = 0
            
            if st.session_state.current_tech_index < len(candidate_info["tech_stack"]):
                st.session_state.current_tech = candidate_info["tech_stack"][st.session_state.current_tech_index]
                next_question = generate_tech_question(model, st.session_state.current_tech)
                candidate_info["questions"].append(next_question)
                return f"Now, let's talk about your experience with {st.session_state.current_tech}. {next_question}"
            else:
                # All technologies covered
                st.session_state.current_state = "farewell"
                
                # Add sentiment score and grade the candidate
                candidate_info["sentiment_score"] = st.session_state.sentiment_score
                candidate_info["grade"] = grade_candidate(model, candidate_info)
                
                # Save the candidate data
                st.session_state.all_candidates.append(candidate_info.copy())
                
                return "Thank you for answering all the technical questions! Your responses have been recorded. A TalentScout recruiter will contact you soon if your profile matches our open positions. Is there anything else you'd like to add before we conclude?"
    
    elif current_state == "farewell":
        return "Thank you for your time! Your information has been recorded. Feel free to reach out if you have any questions about the process. Have a great day!"
    
    else:
        # Use Gemini for more dynamic responses
        chat_context = create_system_prompt()
        for msg in st.session_state.messages[-5:]:  # Use only last 5 messages for context
            chat_context += f"\n{msg['role']}: {msg['content']}"
        
        chat_context += f"\nUser: {user_input}\nAssistant:"
        
        response = model.generate_content(chat_context)
        return response.text

# Admin authentication
def authenticate_admin(username, password):
    # In a real application, you would check against a secure database
    # For demo purposes, we use a simple credential check
    return username == "admin" and password == "password"

# Reset the chat for a new candidate
def reset_chat():
    st.session_state.messages = []
    st.session_state.candidate_info = {
        "name": None,
        "email": None,
        "phone": None,
        "experience": None,
        "desired_position": None,
        "location": None,
        "tech_stack": [],
        "answers": [],
        "questions": [],
        "grade": None
    }
    st.session_state.current_state = "greeting"
    st.session_state.current_tech = None
    st.session_state.current_tech_index = 0
    st.session_state.questions_asked = 0
    st.session_state.sentiment_score = 0
    st.session_state.initialized = False

# Main application
def main():
    st.title("TalentScout Hiring Assistant")
    
    # Sidebar for configuration and candidate information
    with st.sidebar:
        # Reset button for all users (not just admin)
        if st.button("Start New Interview", key="reset_chat_user"):
            reset_chat()
            st.rerun()
            
        st.header("Admin Panel")
        
        # Admin login
        if not st.session_state.admin_logged_in:
            with st.expander("Admin Login", expanded=False):
                admin_username = st.text_input("Username", key="admin_username")
                admin_password = st.text_input("Password", type="password", key="admin_password")
                login_button = st.button("Login")
                
                if login_button:
                    if authenticate_admin(admin_username, admin_password):
                        st.session_state.admin_logged_in = True
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        # Admin controls when logged in
        if st.session_state.admin_logged_in:
            st.success("Admin logged in")
            
            # Generate PDF report
            if st.button("Generate PDF Report", key="generate_pdf"):
                if st.session_state.all_candidates:
                    pdf_path = generate_pdf_report()
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_file,
                            file_name="candidates_report.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.warning("No candidate data available for the report")
            
            # View candidates
            st.subheader("All Candidates")
            if st.session_state.all_candidates:
                # Create a selectbox for candidate emails
                candidate_emails = [c.get("email", f"Unknown-{i}") for i, c in enumerate(st.session_state.all_candidates)]
                selected_candidate_email = st.selectbox("Select Candidate", candidate_emails)
                
                # Find the selected candidate
                selected_candidate = next(
                    (c for c in st.session_state.all_candidates if c.get("email") == selected_candidate_email), 
                    st.session_state.all_candidates[0]
                )
                
                # Display the candidate info
                st.subheader(f"Candidate: {selected_candidate.get('name', 'Unknown')}")
                st.info(f"Email: {selected_candidate.get('email', 'N/A')}")
                st.info(f"Phone: {selected_candidate.get('phone', 'N/A')}")
                st.info(f"Experience: {selected_candidate.get('experience', 'N/A')}")
                st.info(f"Position: {selected_candidate.get('desired_position', 'N/A')}")
                st.info(f"Location: {selected_candidate.get('location', 'N/A')}")
                st.info(f"Tech Stack: {', '.join(selected_candidate.get('tech_stack', []))}")
                
                # Sentiment indicator
                sentiment = selected_candidate.get("sentiment_score", 0)
                st.subheader("Candidate Sentiment")
                if sentiment > 3:
                    st.success("Very Positive")
                elif sentiment > 0:
                    st.info("Positive")
                elif sentiment == 0:
                    st.warning("Neutral")
                else:
                    st.error("Negative")
                
                # Display AI-generated grade
                grade = selected_candidate.get("grade", "Not graded")
                st.subheader("AI Grade")
                
                # Display color code based on AI grade
                if grade >= 8:
                    st.success(f"High potential candidate: {grade}/10")
                elif grade >= 4:
                    st.warning(f"Average potential candidate: {grade}/10")
                else:
                    st.error(f"Low potential candidate: {grade}/10")
                
                # Display Q&A
                if "questions" in selected_candidate and "answers" in selected_candidate:
                    st.subheader("Technical Assessment")
                    for i, (q, a) in enumerate(zip(
                        selected_candidate.get("questions", []), 
                        selected_candidate.get("answers", [])
                    )):
                        st.write(f"**Q{i+1}:** {q}")
                        st.write(f"**A{i+1}:** {a}")
                        st.divider()
            else:
                st.info("No candidates have completed the interview yet")
        
        # Regular user info display (for both admin and non-admin)
        st.divider()
        st.header("Candidate Information")
        if st.session_state.candidate_info["name"]:
            st.info(f"Name: {st.session_state.candidate_info['name']}")
        if st.session_state.candidate_info["email"]:
            st.info(f"Email: {st.session_state.candidate_info['email']}")
        if st.session_state.candidate_info["phone"]:
            st.info(f"Phone: {st.session_state.candidate_info['phone']}")
        if st.session_state.candidate_info["experience"]:
            st.info(f"Experience: {st.session_state.candidate_info['experience']}")
        if st.session_state.candidate_info["desired_position"]:
            st.info(f"Position: {st.session_state.candidate_info['desired_position']}")
        if st.session_state.candidate_info["location"]:
            st.info(f"Location: {st.session_state.candidate_info['location']}")
        if st.session_state.candidate_info["tech_stack"]:
            st.info(f"Tech Stack: {', '.join(st.session_state.candidate_info['tech_stack'])}")
    
    # Initialize model
    try:
        model = configure_genai()
    except Exception as e:
        st.error(f"Error configuring API: {e}")
        model = None
    
    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Auto-start conversation if it's the first load
    if not st.session_state.initialized and model:
        # Add assistant message to chat history
        initial_message = "Welcome to TalentScout! I'm your hiring assistant, and I'll help with the initial screening process. Could you please tell me your full name?"
        st.session_state.messages.append({"role": "assistant", "content": initial_message})
        st.session_state.current_state = "ask_name"
        st.session_state.initialized = True
        st.rerun()
    
    # Chat input
    if user_input := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get assistant response
        if model:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    assistant_response = process_user_input(model, user_input)
                    st.markdown(assistant_response)
                    
            # Add assistant response to message history
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Rerun to update the UI
            time.sleep(0.5)  # Give a moment for the UI to update
            st.rerun()
        else:
            st.error("Unable to configure Gemini API. Please check your API key.")

def save_candidate(candidate_info, model):
    # Don't save if already saved
    if any(c.get("email") == candidate_info["email"] for c in st.session_state.all_candidates):
        return
        
    # Add sentiment score to the candidate info
    candidate_info["sentiment_score"] = st.session_state.sentiment_score
    
    # Grade the candidate
    candidate_info["grade"] = grade_candidate(model, candidate_info)
    
    # Create a copy to avoid reference issues
    st.session_state.all_candidates.append(candidate_info.copy())


if __name__ == "__main__":
    main()