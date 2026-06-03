"""
Gemini AI service for disaster management chat
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

GEMINI_API_KEY = os.getenv('gemini_key', '')
print("GEMINI_API_KEY loaded:", GEMINI_API_KEY[:10] + "..." if GEMINI_API_KEY else "NOT FOUND")
print("Env path:", os.path.join(os.path.dirname(__file__), '..', '.env'))

SYSTEM_PROMPT = """You are DisasterGuard AI, a specialized assistant for disaster management and safety in Pakistan. 

RULES:
1. ONLY answer questions related to:
   - Natural disasters (floods, earthquakes, wildfires, cyclones, landslides, droughts)
   - Weather conditions and forecasts in Pakistan
   - Emergency preparedness and safety guidelines
   - First aid and emergency response procedures
   - Disaster risk management and mitigation
   - Emergency contact numbers in Pakistan (115, 1122, 1150, etc.)
   - Historical disaster data for Pakistan

2. NEVER answer:
   - General chat, jokes, or casual conversation
   - Questions unrelated to disasters or safety
   - Personal questions about yourself beyond your role
   - Political or controversial topics
   - Medical advice beyond basic first aid for emergencies

3. ALWAYS:
   - Provide concise, actionable information
   - Include Pakistani context when relevant
   - Use Urdu terms if appropriate, but primarily English
   - Give practical safety steps when applicable
   - Reference official Pakistani emergency numbers when relevant

4. If asked something outside your scope, politely respond:
   "I'm focused on disaster management and safety. Please ask about weather, disasters, emergency preparedness, or safety guidelines for Pakistan."
"""


def get_ai_response(message: str):
    """Get AI response from Gemini API for disaster-related queries"""
    if not GEMINI_API_KEY:
        return {
            "response": "I'm here to help with disaster safety! For real-time responses, please ensure the AI service is configured with a valid API key. I can give you general safety guidelines about floods, earthquakes, wildfires, and emergency preparedness in Pakistan."
        }
    
    try:
        # Use Gemini 2.5 Flash-Lite - latest lightweight free model
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
        
        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"{SYSTEM_PROMPT}\n\nUser question: {message}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192
            }
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(gemini_url, json=request_body, headers=headers)
        print("Response status code:", response.status_code)
        response_json = response.json()
        print("Response JSON:", response_json)
        
        if "candidates" in response_json and len(response_json["candidates"]) > 0:
            ai_response = response_json["candidates"][0]["content"]["parts"][0]["text"]
        else:
            ai_response = "I'm sorry, I couldn't process that right now. Please try again later."
        
        return {"response": ai_response}
        
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        import traceback
        print("Stack trace:", traceback.format_exc())
        return {
            "response": "I'm sorry, I couldn't connect to the AI service right now. Please check your API configuration or try again later. In the meantime, here are emergency numbers for Pakistan:\n- National Emergency: 1122\n- Rescue 1122: 1122\n- Police: 15\n- Ambulance: 115\n- Fire Brigade: 16"
        }
