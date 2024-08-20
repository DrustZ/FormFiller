from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from Storage.ReminderManager import ReminderManager
from Utils.ReminderCommandParser import ReminderCommandParser
from Utils.ReminderResponder import ReminderResponder
import base64
from typing import Optional
import binascii

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize components
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

reminder_manager = ReminderManager(api_key)
reminder_responder = ReminderResponder(api_key)
command_parser = ReminderCommandParser(api_key, reminder_manager)

class ReminderRequest(BaseModel):
    inquiry: str
    img: Optional[str] = ""

def safe_decode_base64(s):
    """Safely decode base64, adding padding if necessary."""
    s = s.strip()
    try:
        return base64.b64decode(s)
    except binascii.Error:
        # If padding is incorrect, add padding and try again
        missing_padding = len(s) % 4
        if missing_padding:
            s += '=' * (4 - missing_padding)
        return base64.b64decode(s)

@app.post("/reminder")
async def handle_reminder(request: ReminderRequest):
    print(f"Received inquiry: {request.inquiry}")
    rq = request.inquiry.lower()
    if rq.startswith("remind me") or rq.startswith("remember"):
        # Create a new reminder
        reminder_id = reminder_manager.add_reminder(request.inquiry)
        return f"Memory added with ID: {reminder_id}"
    
    image_path = None
    description = ""
    if request.img:
        # Save the image temporarily
        image_path = "temp_image.jpg"
        img_data = safe_decode_base64(request.img)
        with open(image_path, "wb") as f:
            f.write(img_data)

    try:
        if request.img:
            description, results = command_parser.process_command_with_image(request.inquiry, image_path)
        else:
            results = command_parser.process_command(request.inquiry)

        response = reminder_responder.generate_response(request.inquiry, description, results, image_path)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)