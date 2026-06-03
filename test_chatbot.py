import requests
import json

# Test the chatbot API
def test_chatbot():
    url = "http://localhost:5000/api/ai/chat"
    
    test_messages = [
        "What is the flood risk in Karachi?",
        "Emergency numbers in Pakistan",
        "What should I do during an earthquake?"
    ]
    
    print("Testing Chatbot API...\n")
    
    for message in test_messages:
        print(f"User: {message}")
        try:
            response = requests.post(url, json={"message": message})
            data = response.json()
            print(f"AI: {data.get('response', 'No response')}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    test_chatbot()
