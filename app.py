import streamlit as st
import google.generativeai as genai
import re
import time
import json
import os
from dotenv import load_dotenv

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
    }
if "current_state" not in st.session_state:
    st.session_state.current_state = "greeting"
if "tech_questions" not in st.session_state:
    st.session_state.tech_questions = {}
if "current_tech" not in st.session_state:
    st.session_state.current_tech = None
if "questions_asked" not in st.session_state:
    st.session_state.questions_asked = 0
if "sentiment_score" not in st.session_state:
    st.session_state.sentiment_score = 0
if "language" not in st.session_state:
    st.session_state.language = "English"
if "initialized" not in st.session_state:
    st.session_state.initialized = False

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
    positive_words = ['happy', 'great', 'good', 'excellent', 'thank', 'appreciate', 'excited']
    negative_words = ['bad', 'poor', 'frustrated', 'annoyed', 'difficult', 'problem', 'issue']
    
    text = text.lower()
    sentiment = 0
    
    for word in positive_words:
        if word in text:
            sentiment += 1
    
    for word in negative_words:
        if word in text:
            sentiment -= 1
            
    return sentiment

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
    4. Current language: {st.session_state.language}
    
    Current candidate information: {json.dumps(st.session_state.candidate_info, indent=2)}
    Current state: {st.session_state.current_state}
    
    Rules:
    - Keep responses concise and professional.
    - Focus on collecting required information in a conversational manner.
    - Generate total 5 meaningful technical questions for tech stacks.
    - Do not hallucinate or make up information about the candidate.
    - Do not deviate from the purpose of candidate screening.
    - If the candidate wants to end the conversation, thank them and close politely.
    """

# Generate tech questions
def generate_tech_questions(model, tech):
    response = model.generate_content(
        f"""Generate exactly 5 unique and thought-provoking technical interview questions to assess a candidate's proficiency in {tech}.  
        Ensure the questions vary in difficulty (ranging from fundamental to advanced) and cover different aspects of the technology, including theoretical concepts, problem-solving, real-world applications, debugging, and optimization.  
        The questions should require critical thinking and not be simple definitions or trivia.  
        Return only the questions in a JSON array format like this:  
        ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"]  
        """
    )
    try:
        questions_text = response.text.strip()
        # Extract JSON array if wrapped in backticks
        if "```json" in questions_text:
            questions_text = questions_text.split("```json")[1].split("```")[0].strip()
        elif "```" in questions_text:
            questions_text = questions_text.split("```")[1].strip()
        
        questions = json.loads(questions_text)
        return questions[:5]  # Limit to 5 questions
    except Exception as e:
        st.error(f"Error parsing questions: {e}")
        return [f"Can you explain your experience with {tech}?",
                f"What are the key features of {tech}?",
                f"Describe a challenging problem you solved using {tech}.",
                f"How do you stay updated with the latest developments in {tech}?",
                f"What best practices do you follow when working with {tech}?"]

# Process user input
def process_user_input(model, user_input):
    current_state = st.session_state.current_state
    candidate_info = st.session_state.candidate_info
    
    # Check for exit request
    if check_exit(user_input):
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
        
        # Generate questions for each technology
        for tech in tech_stack:
            if tech not in st.session_state.tech_questions:
                st.session_state.tech_questions[tech] = generate_tech_questions(model, tech)
        
        st.session_state.current_state = "tech_questions"
        st.session_state.current_tech = tech_stack[0] if tech_stack else None
        
        if st.session_state.current_tech:
            return f"Great! Let's assess your knowledge of {st.session_state.current_tech}. {st.session_state.tech_questions[st.session_state.current_tech][0]}"
        else:
            st.session_state.current_state = "farewell"
            return "I notice you didn't specify any technologies. Unfortunately, we need this information to proceed. Would you like to try again and list your technical skills?"
    
    elif current_state == "tech_questions":
        # Record the answer and move to the next question or technology
        st.session_state.questions_asked += 1
        
        if st.session_state.questions_asked >= len(st.session_state.tech_questions[st.session_state.current_tech]):
            # Move to the next technology
            current_tech_index = candidate_info["tech_stack"].index(st.session_state.current_tech)
            if current_tech_index + 1 < len(candidate_info["tech_stack"]):
                st.session_state.current_tech = candidate_info["tech_stack"][current_tech_index + 1]
                st.session_state.questions_asked = 0
                return f"Now, let's talk about your experience with {st.session_state.current_tech}. {st.session_state.tech_questions[st.session_state.current_tech][0]}"
            else:
                # All technologies covered
                st.session_state.current_state = "farewell"
                return "Thank you for answering all the technical questions! Your responses have been recorded. A TalentScout recruiter will contact you soon if your profile matches our open positions. Is there anything else you'd like to add before we conclude?"
        else:
            # Ask the next question for the current technology
            question_index = st.session_state.questions_asked
            return f"Thank you for your response. {st.session_state.tech_questions[st.session_state.current_tech][question_index]}"
    
    elif current_state == "farewell":
        return "Thank you for your time! Your information has been recorded. Feel free to reach out if you have any questions about the process. Have a great day!"
    
    else:
        # Use Gemini for more dynamic responses
        chat_context = create_system_prompt()
        for msg in st.session_state.messages:
            chat_context += f"\n{msg['role']}: {msg['content']}"
        
        chat_context += f"\nUser: {user_input}\nAssistant:"
        
        response = model.generate_content(chat_context)
        return response.text

# Main application
def main():
    st.title("TalentScout Hiring Assistant")
    
    # Sidebar for configuration and candidate information
    with st.sidebar:
        st.header("Configuration")
        
        # Language selection
        languages = ["English", "Spanish", "French", "German", "Chinese", "Japanese"]
        st.session_state.language = st.selectbox("Select Language", languages, index=languages.index(st.session_state.language))
        
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
        
        # Sentiment display
        st.divider()
        st.header("Candidate Sentiment")
        sentiment = st.session_state.sentiment_score
        if sentiment > 3:
            st.success("Very Positive")
        elif sentiment > 0:
            st.info("Positive")
        elif sentiment == 0:
            st.warning("Neutral")
        else:
            st.error("Negative")
    
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

if __name__ == "__main__":
    main()