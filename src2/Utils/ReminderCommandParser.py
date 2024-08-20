import base64
import json
from .Util import Utils
from openai import OpenAI
from typing import Optional, Tuple, List

class ReminderCommandParser:
    def __init__(self, api_key: str, reminder_manager):
        self.client = OpenAI(api_key=api_key)
        self.reminder_manager = reminder_manager

    def _get_image_description(self, image_path: str, user_input: str) -> str:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = self.client.chat.completions.create(
        model="gpt-4o",
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"""You are a smart assistant that helps the user to retrieve relevant reminders from the query '{user_input}' and the image.
                        
                        The reminders has two components: the things to remind and the trigger conditions, such as `remind me to buy milk when I pass by the grocery store`, where `grocery store`` is the trigger condition.
                     
                        Your task is to generate a list of queries that will be used to search the reminder database for relevant reminders. When analyze the image, consider any visible text, the scene and objects.
                        
                        For example, you can identify `wholefoods`, `raining`,`umbrella`, `using iphone to taking photos`, `5:15pm`, when the image is a person taking picture in front of wholefoods in a rainy day, with a clock showing 5:15pm, since these are the potential triggers / contents for the reminders. 

                        In this way, you then generate a image_description that contains all those identified contents into a search query.
                        
                        please reply in the json format, with

                        {{
                            "queries": [
                                "wholefoods, grocery store",
                                "5:15 pm",
                                ...
                            ], 
                            "image_description": "a person taking picture in front of wholefoods in a rainy day, with a clock showing 5:15pm"
                        }}

                        """},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return Utils.extractValidJson(response.choices[0].message.content)

    def _generate_questions_from_image(self, image_path, user_input):
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"""
                        You are tasked with recognizing the content of a picture and identifying any questions that needs to be answered from the image and the user's question: "{user_input}".
                        
                        If it's a form or has multiple questions relevant to the user's input, create a question for each field. 
                        
                        For example, if the user takes a picture of a form with fields for name, address, and license plate number, but name and address is already filled, then you should generate questions for "What is the licence plate number?". The query is then used to search a knowledge database.

                        If the user already asks a question, generate only that question with more info on the image. 
                        
                        For example, if the user asks "Which book should I buy?", (maybe they had some reminders to buy some books), then you should generate a question "What is the book to buy, among books of xxx (those are recognized books from the picture)?". 

                        If the user asks "what is the class time" with a image of tennis rackte, then you should generate a question "What is the class time for tennis class?".

                        Ensure each question is self-contained and understandable on its own, include any necessary info from the image.
                        
                        Return the questions in a JSON format like this:
                        {{
                            "questions": [
                                "What is the user's steam login password?",
                                "What is the book title visible in the image?",
                                ...
                            ],
                            "image_description": "steam login page with password field visible, and a bookshelf with book titles behind the monitor"
                        }}
                        """},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return Utils.extractValidJson(response.choices[0].message.content)

    def execute_query(self, query_type: str, queries: List[str]) -> List[dict]:
        results = {}
        print(f'processing {query_type} {queries}')
        for query in queries:
            new_results = self.reminder_manager.find_reminders(query).to_dict('records')
            for result in new_results:
                if result['ID'] in results:
                    # Merge new information
                    results[result['ID']]['Relevance'] = min(results[result['ID']]['Relevance'], result['Relevance'])
                    # You might want to update other fields here if necessary
                else:
                    results[result['ID']] = result
        return list(results.values())

    def process_command_with_image(self, user_input: str, image_path: str):
        result = None
        if any(keyword in user_input.lower() for keyword in ["reminder", "reminders"]):
            result = self._get_image_description(image_path, user_input)
            queries = [result['image_description']]
        else:
            result = self._generate_questions_from_image(image_path, user_input)
            queries = result['questions']
        return result['image_description'], self.execute_query('image', queries)

    def process_command(self, user_input: str):
        return self.execute_query('text', [user_input])
        
