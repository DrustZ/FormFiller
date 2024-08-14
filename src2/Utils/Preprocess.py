import os
import re
import base64
import requests
from pdf2image import convert_from_path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from Util import Utils
from tqdm import tqdm
from openai import OpenAI

class Preprocessor:
    def __init__(self, api_key=None):
        self.page_pattern = re.compile(r'\bPage\s+\d+', re.IGNORECASE)
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = OpenAI()

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    def extract_text_from_url(url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()

    def process_image_batch(self, image_batch, user_description="this is my personal data"):
        image_contents = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(img_path)}"}
            } for img_path in image_batch
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", 
                         "text": '''
                         These are pages from a PDF document. The user is trying to use the content to create a personal knowledge base, which can be used for future form filling of the user. 
                         
                         Please provide a detailed description of their content, including any text, images, tables, or other visual elements. 
                         
                         Focus on extracting and summarizing the key information presented on these pages. Ignore the contents that are not relevant to the user themselves. 
                         
                         Maintain the order of information as it appears in the pages, and always include a summary of the document in the first line of the response starting with the keyword summary.
                         
                         Here's the user's description of the file: 
                         ''' + user_description},
                        *image_contents
                    ]
                }
            ],
            max_tokens=4000
        )
        return response.choices[0].message.content

    def extract_questions_from_form(self, image_batch, user_description="this is a form to fill"):
        image_contents = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{self.encode_image(img_path)}"}
            } for img_path in image_batch
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", 
                         "text": '''
                         You are tasked with recognizing the content of a PDF and identifying any forms that require filling.
                         
                         For each fillable field in the form, construct a question that is sufficient for answering directly without needing to read the entire PDF.
                         
                         Exclude the already-filled fields, current date, and signature fields.
                         
                         Handle ambiguous fields or grouped fields by combining related fields into a single, coherent question. When constructing questions, follow these guidelines:

                         1. Each field's identifier will be represented as 'field_name' (same as on the form).
                         2. Each constructed question will be represented as 'question'.
                         3(a). Group similar or related fields into a single question to avoid redundancy. For example, if multiple fields relate to education history, combine them into a single question asking for all relevant details. 
                         3(b). If a field is ambiguous or requires additional context that will be gained from other info from the pdf, provide minimal but sufficient info. Specifically, if the field relies on other fields, group them together. For example, if one field is asking about a math question, and another is asking a follow up question, group them together.
                         4. Present the questions IN THE ORDER of the fields as they appear in the form.
                         5. Ensure each question is self-contained and understandable on its own.
                         6. Ensure that EVERY SINGLE BLANK FIELD is covered in order by the questions.
                         7. Use clear and concise language for the questions.
                         
                         Here is the JSON format to follow:
                         {"questions": [
                            {
                                "field_name": "field identifier 1 (strictly as shown in form)",
                                "question": "What is your full name?"
                            },
                            {
                                "field_name": "field identifier 2",
                                "question": "What is your date of birth?"
                            },
                            {
                                "field_name": "group_education_history(field_identifiers)",
                                "question": "Please provide the five most recent education experiences, including school name, level, and address."
                            },
                            {
                                "field_name": "group_address_information(field_identifiers)",
                                "question": "What is your complete address, including street name, PO Box, and postal code?"
                            }
                        ]}
                        
                        Here's the user's description of the file:
                        ''' + user_description},
                        *image_contents
                    ]
                }
            ],
            max_tokens=4000
        )
        return response.choices[0].message.content

    def process_pdf_form(self, file_path, comment) -> dict:
        questions = self.process_pdf(file_path, comment, self.extract_questions_from_form)
        questions = [Utils.extractValidJson(q) for q in questions]
        questions = [q for q in questions if q is not None]
        combined_questions = {"questions": []}
        for item in questions:
            combined_questions["questions"].extend(item["questions"])
        
        return combined_questions

    def process_pdf(self, file_path, comment, process_func) -> list[str]:
        images = convert_from_path(file_path)
        temp_image_paths = []
        for i, image in enumerate(tqdm(images, desc="Converting PDF to images", unit="page")):
            temp_path = f"temp_image_{i}.jpg"
            image.save(temp_path, "JPEG")
            temp_image_paths.append(temp_path)
        
        batch_size = 3
        summaries = []
        for i in tqdm(range(0, len(temp_image_paths), batch_size), desc="Analyzing PDF pages", unit="batch"):
            batch = temp_image_paths[i:i+batch_size]
            batch_summary = process_func(batch, comment)
            summaries.append(batch_summary)

        # Clean up temporary files
        for temp_path in temp_image_paths:
            os.remove(temp_path)
        return summaries

    def extract_knowledge(self, file_path, comment, tmp_file_path="temp.txt"):
        _, file_extension = os.path.splitext(file_path)
        
        if file_extension.lower() in ['.pdf']:
            summaries = self.process_pdf(file_path, comment, self.process_image_batch)
            content = "\n\n".join(summaries)
        elif file_extension.lower() in ['.jpg', '.jpeg', '.png']:
            content = self.process_image_batch([file_path], comment)
        elif file_extension.lower() in ['.txt', '.md']:
            with open(file_path, 'r') as file:
                content = file.read()
        elif urlparse(file_path).scheme in ['http', 'https']:
            content = self.extract_text_from_url(file_path)
        else:
            return "Unsupported file type"

        with open(tmp_file_path, "w") as f:
            f.write(content)
        return content
    
    import re

    def extract_summaries(self, lines):
        start_summary = []
        end_summary = []
        summary_end = 0

        for i, line in enumerate(lines):
            if line.strip().lower().startswith(('conclusion', 'summary')):
                break
            if line.strip():
                start_summary.append(line)
            else:
                summary_end = i
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().lower().startswith(('conclusion', 'summary')):
                end_summary = lines[i:]
                break

        main_content = lines[summary_end:len(lines)-len(end_summary)]
        return start_summary, main_content, end_summary
    
    def find_page_breaks(self, content):
        return [i for i, line in enumerate(content) if self.page_pattern.search(line)]

    def create_batch(self, content, start_summary, end_summary):
        return '\n'.join(start_summary + content + end_summary)

    def split_content(self, content, lines_per_batch=200, overlap=5):
        lines = content.split('\n')
        start_summary, main_content, end_summary = self.extract_summaries(lines)
        page_breaks = self.find_page_breaks(main_content)

        batches = []
        current_batch = []
        current_line_count = 0

        def add_to_batch(line):
            nonlocal current_batch, current_line_count
            current_batch.append(line)
            current_line_count += 1

        def finalize_batch():
            nonlocal current_batch, current_line_count, batches
            if current_batch:
                batches.append(self.create_batch(current_batch, start_summary, end_summary))
                current_batch = []
                current_line_count = 0

        for i, line in enumerate(main_content):
            if i in page_breaks:
                if current_line_count >= lines_per_batch:
                    finalize_batch()
                elif current_line_count > 0:
                    add_to_batch(line)
                    continue

            add_to_batch(line)

            if current_line_count >= lines_per_batch:
                next_page_break = next((pb for pb in page_breaks if pb > i), None)
                if next_page_break is None or next_page_break - i > overlap:
                    finalize_batch()

        finalize_batch()  # Add any remaining content as the last batch
        return batches