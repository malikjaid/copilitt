from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import requests
import speech_recognition as sr
from gtts import gTTS
import playsound

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://healthorbitaidev210772056557.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2023-03-15-preview")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "949ef1d4da1a44759286a068bb4aef87")

app = FastAPI()

# Serve static files (for JavaScript and CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Function to convert text to speech
def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    playsound.playsound("response.mp3")
    os.remove("response.mp3")

# Function to recognize speech
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            command = recognizer.recognize_google(audio)
            print(f"You said: {command}")
            return command
        except sr.UnknownValueError:
            print("Sorry, I could not understand the audio.")
            return None
        except sr.RequestError:
            print("Could not request results from Google Speech Recognition service.")
            return None

# Function to summarize answers using Azure OpenAI
def summarize_answers(answers):
    prompt = "Please summarize the following responses:\n" + "\n".join(f"{q} {a}" for q, a in answers.items())
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_OPENAI_API_KEY
    }
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150  # Adjust max tokens based on your needs
    }

    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return "Sorry, I couldn't summarize the responses."

# HTML for the front-end interface
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nurse</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #f4f4f9, #d1e3ff);
            color: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            transition: background 0.5s;
        }
        .container {
            background: rgba(255, 255, 255, 0.8);
            border-radius: 15px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            padding: 40px;
            text-align: center;
            width: 90%;
            max-width: 400px;
            backdrop-filter: blur(10px);
        }
        h1 {
            color: #4A90E2;
            margin-bottom: 20px;
            text-shadow: 1px 1px 5px rgba(0, 0, 0, 0.2);
        }
        #summary {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #4A90E2;
            border-radius: 5px;
            background: linear-gradient(135deg, #e9f5ff, #cfe9ff);
            display: none;
            transition: all 0.3s;
        }
        #listening {
            display: none;
            font-size: 18px;
            color: #FFA500;
            animation: fadeIn 1s;
        }
        .mic-button {
            background: linear-gradient(135deg, #4A90E2, #5DADE2);
            border: none;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            color: white;
            font-size: 24px;
            cursor: pointer;
            outline: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            transition: background 0.3s, transform 0.3s;
        }
        .mic-button:hover {
            background: linear-gradient(135deg, #357ABD, #4A90E2);
            transform: scale(1.1);
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Nurse Copilot</h1>
        <button class="mic-button" onclick="startChat()">🎤</button>
        <div id="listening">Listening...</div>
        <div id="summary"></div>
    </div>

    <script>
        function startChat() {
            const summaryDiv = document.getElementById('summary');
            const listeningDiv = document.getElementById('listening');
            summaryDiv.innerHTML = "";
            listeningDiv.style.display = "block"; // Show listening message
            summaryDiv.style.display = "none"; // Hide summary initially
            
            fetch('/start-chat')
                .then(response => response.json())
                .then(data => {
                    listeningDiv.style.display = "none"; // Hide listening message
                    summaryDiv.innerHTML = "<strong>Summary:</strong> " + data.summary;
                    summaryDiv.style.display = "block"; // Show summary
                })
                .catch(error => {
                    console.error('Error:', error);
                    listeningDiv.style.display = "none"; // Hide listening message
                    summaryDiv.innerHTML = "An error occurred.";
                    summaryDiv.style.display = "block"; // Show error message
                });
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return html_content

@app.get("/start-chat")
async def start_chat():
    questions = [
        "What is your name?",
        "How old are you?",
        "What is your favorite color?",
        "What do you do for a living?",
        "Do you have any hobbies?"
    ]
    
    answers = {}

    for question in questions:
        for attempt in range(2):  # Allow up to 2 attempts for each question
            speak(question)
            user_input = recognize_speech()
            if user_input:
                answers[question] = user_input
                break  # Exit the loop if user provides input
            else:
                if attempt == 0:  # Only speak the question again if this is the first attempt
                    speak("I didn't catch that. Please answer the question.")
    
    # Summarize the answers
    summary = summarize_answers(answers)

    # Thank the user after asking all questions
    speak("Thank you for your responses.")
    
    return {"summary": summary}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
