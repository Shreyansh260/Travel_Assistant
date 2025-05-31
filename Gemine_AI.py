# Copyright (c) 2025 Shriyansh Singh Rathore
# Licensed under the MIT License

import google.generativeai as genai

# Configure with your Gemini API key
genai.configure(api_key="your_gemini_api_key_here")

# Select your model
model = genai.GenerativeModel("models/gemini-1.5-pro-001")

def chat_with_gemini():
    print("Welcome to Gemini Chatbot! (type 'exit' to quit)\n")
    conversation_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        
        # Prepare conversation context (optional, for simple context)
        conversation_history.append(f"User: {user_input}")
        prompt = "\n".join(conversation_history) + "\nAssistant:"

        # Generate response
        response = model.generate_content(prompt)
        bot_reply = response.text.strip()

        print("Bot:", bot_reply)

        # Save bot reply to history to keep context
        conversation_history.append(f"Assistant: {bot_reply}")

if __name__ == "__main__":
    chat_with_gemini()
