import base64
from openai import OpenAI
from typing import List, Optional, Dict

class ReminderResponder:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, user_query: str, description, memories, image_path) -> str:
        system_prompt = """
        You are an voice AI assistant responding to user queries based on their reminders and memories. 

        Your task is to provide helpful, concise answers based on the given information.

        Format your responses in a voice-interface friendly way:
        - Do not include any information about the reminder or memories that is not relevant to both the user query and the image content.
        - Reply as lazy as you can yet still answer the question.
        - For short answers, respond directly.
        - For longer answers or lists, provide a brief overview followed by key points.
        - If there's an image, then the user is explicitly asking the question about the image. If the memories is not relevant to the image description, do not use them, even they might be relevant to the query.
        - If there's no answer just say there's no.
        - Try answer in one phrase.
        - If the user askes about what the relevant reminders to the image are, you should only include the reminders that are relevant to the image description (only reminders, not facts that are remembered).

        For example, if the user query is "What are my reminders?", and took a picture of a grocery store, and a clock showing 5pm, but there's no relevant memories about shopping or 5pm, you should respond with "You don't have any reminders.", even there might be reminders about other things, and do not include those reminders in the response.

        However, if there's a memory about buying milk when passing whole foods or go to dentist at 5:15pm, you should report that since they're relevant to the query and the image description.

        Another example: if the user query is "look and tell me the price of this thing", and the image is a picture of phone, and if there's reminder about this phone's price, you reply "the price is xxx", if there's no reminder about the phone's price, you reply "there's no info about the phone's price".
        """

        user_prompt = f"User Query: {user_query}\n\nRelevant Memories/Reminders:\n"
        for memory in memories:
            user_prompt += f"- {memory.get('Content', '')}\n"
        if image_path:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                user_prompt += f"\n\n The user also took a picture with the query, description of the image is: {description}\n\n"
                print(user_prompt)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ]
            model = "gpt-4o"
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            model = "gpt-4o"

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500
        )

        return response.choices[0].message.content

    def format_voice_response(self, response: str) -> Dict[str, str]:
        # Split the response into sentences
        sentences = response.split('. ')
        
        # If the response is short, return it as is
        if len(sentences) <= 3:
            return {"summary": response, "details": None}
        
        # Otherwise, create a summary and details
        summary = '. '.join(sentences[:2]) + '.'
        details = '. '.join(sentences[2:])
        
        return {"summary": summary, "details": details}

    def respond(self, user_query: str, memories: List[Dict], image_path: Optional[str] = None) -> Dict[str, str]:
        full_response = self.generate_response(user_query, memories, image_path)
        return self.format_voice_response(full_response)