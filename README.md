# TalentScout Hiring Assistant

TalentScout Hiring Assistant is an AI-powered technical recruitment tool that automates initial candidate screening through intelligent conversation, technical assessment, and comprehensive evaluation.

## 🔥 Demo

- Live Demo: [Click Here](https://talentscout-chatbot.onrender.com)
- Explaner Video: [Watch in Loom](https://www.loom.com/share/0064d9cfb80b4886978cabd174246c19?sid=0d21e9cd-8ff0-41ec-a63d-45175cd80652)

## 🚀 Features

- **Conversational Interface**: Natural dialogue-based candidate screening
- **Dynamic Technical Assessment**: Technology-specific questions adapted to candidate skills
- **Sentiment Analysis**: Evaluate candidate communication and enthusiasm
- **AI-Powered Grading**: Objective candidate evaluation based on multiple factors
- **Admin Dashboard**: Review candidate performance and generate reports
- **PDF Report Generation**: Create professional candidate summary documents

## 📋 Prerequisites

- streamlit>=1.22.0
- google-generativeai>=0.3.0
- python-dotenv>=1.0.0
- pandas>=1.3.5
- reportlab>=3.6.12

## 🔧 Installation

1. Clone the repository:
   ```
   git clone https://github.com/prantikm07/TalentScout-Chatbot.git
   cd TalentScout-Chatbot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## 🚀 Usage

1. Start the application:
   ```
   streamlit run app.py
   ```

2. Access the application in your browser at `http://localhost:8501`

3. For admin access:
   - Click on "Admin Login" in the sidebar
   - Username: `admin`
   - Password: `password`

## 💻 User Guide

### Candidate Experience
1. Respond to the chatbot's greeting with your name
2. Provide requested personal information (email, phone, etc.)
3. List your technical skills when prompted
4. Answer technical questions about each technology in your stack
5. Receive confirmation when the interview is complete

### Admin Features
1. View all completed candidate interviews
2. Select individual candidates to review their responses
3. See sentiment analysis and AI-generated grades
4. Generate and download PDF reports with candidate details


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

If you have any questions, feel free to contact me via:
- Email: [prantik25m@gmail.com](mailto:prantik25m@gmail.com)
- LinkedIn: [Prantik Mukhopadhyay](https://www.linkedin.com/in/prantikm07/)