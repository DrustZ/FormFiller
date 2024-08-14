import json
from Util import Utils

class CompleteFormProcessor():
    def __init__(self, openAI_client, memory_manager, form_filler, debug=False):
        self.memory_manager = memory_manager
        self.form_filler = form_filler
        self.client = openAI_client
        self.pdf_cache = {}
        self.question_with_answers = []
        self.debug = debug

    def handle(self, data):
        form_fields = data.get('formFields', [])
        website_info = data.get('websiteOverview', {})
        comment = data.get('comment', '')
        url = data.get('url', '')

        print('Received form data')
        # Step 1: Classify and generate questions
        classification_and_questions = self.classify_and_generate_questions(form_fields, website_info, comment, url)

        print(classification_and_questions)
        if not classification_and_questions['form_valid']:
            self.write({"fieldValues": None})
            return

        # Step 2: Retrieve memories for questions
        questions = classification_and_questions['questions']
        q_w_m = self.form_filler.retrieve_memories_for_questions(questions)

        # Step 3: Group questions and memories
        grouped_batches = self.form_filler.group_questions_and_memories(q_w_m)
        
        print('Questions formed, now filling...')
        # Step 4: Fill form
        filled_form = {}
        for batch in grouped_batches:
            batch_filled_form = self.form_filler.fill_form(batch, comment)
            # Update q_w_m with the answers
            for question in q_w_m:
                if question['id'] in batch_filled_form:
                    question['answer'] = batch_filled_form[question['id']]
                    filled_form[question['field_name']] = question['answer']
        print(filled_form)
        return {"fieldValues": filled_form}

    def classify_and_generate_questions(self, form_fields, website_info, comment, url):
        # Implement chunking logic
        chunks = self.create_chunks(form_fields, website_info, comment, url)
        
        all_results = []
        for chunk in chunks:
            result = self.process_chunk(chunk)
            all_results.append(result)

        # Combine results
        combined_result = self.combine_results(all_results)
        return combined_result

    def create_chunks(self, form_fields, website_info, comment, url, chunk_size=2000):
        def word_count(text: str) -> int:
            return len(text.split())
        chunks = []
        current_chunk = []
        current_size = 0

        for field in form_fields:
            field_size = word_count(json.dumps(field))
            if current_size + field_size > chunk_size and current_chunk:
                chunks.append({
                    'formFields': current_chunk,
                    'websiteOverview': website_info,
                    'comment': comment,
                    'url': url
                })
                current_chunk = []
                current_size = 0
            current_chunk.append(field)
            current_size += field_size

        if current_chunk:
            chunks.append({
                'formFields': current_chunk,
                'websiteOverview': website_info,
                'comment': comment,
                'url': url
            })

        return chunks

    def process_chunk(self, chunk):
        prompt = f"""
        Analyze the following form fields and website information:

        Website Overview: {chunk['websiteOverview']}
        URL: {chunk['url']}
        Comment: {chunk['comment']}
        Form Fields: {json.dumps(chunk['formFields'], indent=2)}

        1. Determine if this is a valid form that needs to be filled with user data (not a search form, comment form, etc.).
        2. If valid, generate questions for each form field that would help in filling the form with user data.
        3. Ensure each question is self-contained and understandable on its own.
        4. Present the questions IN THE ORDER of the fields as they appear in the form.
        
        For each fillable field in the form, construct a question that is sufficient for answering directly without needing to read the entire PDF.
                         
        Exclude the already-filled fields, current date, and signature fields.

        Return your analysis in the following JSON format:
        {{
            "form_valid": true/false,
            "questions": [
                {{
                    "field_name": "field identifier (strictly as shown in form as the 'id', which is used for html form filling)",
                    "question": "Generated question for this field"
                }},
                ...
            ]
        }}

        If the form is not valid for user data filling, set "form_valid" to false and leave "questions" as an empty list.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes web forms and generates appropriate questions for automatic form filling."},
                {"role": "user", "content": prompt}
            ]
        )

        return Utils.extractValidJson(response.choices[0].message.content)

    def combine_results(self, results):
        combined_result = {
            "form_valid": any(result['form_valid'] for result in results),
            "questions": []
        }

        for result in results:
            if result['form_valid']:
                combined_result['questions'].extend(result['questions'])

        return combined_result

class SimplifiedWebFormProcessor():
    def __init__(self, openAI_client, memory_manager, form_filler, debug=False):
        self.memory_manager = memory_manager
        self.form_filler = form_filler
        self.client = openAI_client
        self.pdf_cache = {}
        self.question_with_answers = []
        self.debug = debug

    def process(self, data):
        form_fields = data.get('formFields', [])
        website_info = data.get('websiteOverview', {})
        comment = data.get('comment', '')
        url = data.get('url', '')

        print('Received form data')
        
        # Step 1: Retrieve memories for each field
        fields_with_memories = self.retrieve_memories_for_fields(form_fields)

        # Step 2: Group fields and memories
        grouped_batches = self.group_fields_and_memories(fields_with_memories)
        
        print('Fields processed, now filling...')
        # Step 3: Fill form
        filled_fields = []
        for batch in grouped_batches:
            batch_filled_fields = self.fill_form_simple(batch, website_info, comment, url)
            filled_fields.extend(batch_filled_fields)
        print("Filling complete")
        return filled_fields

    def retrieve_memories_for_fields(self, fields):
        fields_with_memories = []
        for field in fields:
            query = f"{field['name']}"
            memories = self.memory_manager.search_memories(query, n_results=3)
            fields_with_memories.append({
                "field": field,
                "memories": [
                    {
                        "id": row['id'],
                        "content": row['document'],
                        "metadata": row['metadata']
                    }
                    for _, row in memories.iterrows()
                ]
            })
        return fields_with_memories

    def group_fields_and_memories(self, fields_with_memories, max_words=3000):
        def word_count(text: str) -> int:
            return len(text.split())
        
        grouped_batches = []
        current_batch = {"fields": [], "memories": []}
        current_word_count = 0
        current_memory_ids = set()

        for item in fields_with_memories:
            field_words = word_count(json.dumps(item['field']))
            
            # Filter out duplicate memories
            unique_memories = []
            memory_words = 0
            for memory in item['memories']:
                if memory['id'] not in current_memory_ids:
                    unique_memory = {
                        "content": memory['content'],
                        "metadata": memory['metadata']
                    }
                    unique_memories.append(unique_memory)
                    memory_words += word_count(memory['content'])
                    current_memory_ids.add(memory['id'])

            item_words = field_words + memory_words

            if current_word_count + item_words > max_words and (
                current_batch["fields"] or current_batch["memories"]):
                
                grouped_batches.append(current_batch)
                current_batch = {"fields": [], "memories": []}
                current_word_count = 0
                current_memory_ids.clear()

            # Add the field
            current_batch["fields"].append(item['field'])
            
            # Add unique memories
            current_batch["memories"].extend(unique_memories)
            
            current_word_count += item_words

        if current_batch["fields"] or current_batch["memories"]:
            grouped_batches.append(current_batch)

        return grouped_batches

    def fill_form_simple(self, batch, website_info, comment, url):
        fields = batch["fields"]
        memories = batch["memories"]
        
        prompt = f"""
        Website Overview: {website_info}
        URL: {url}
        Comment: {comment}

        Form fields to fill:
        {json.dumps(fields, indent=2)}

        Relevant memories:
        {json.dumps(memories, indent=2)}

        Based on the provided information and memories, fill out the form fields. Return a list of objects (with the key as "form"), where each object contains the following properties:
        - id: the field's 'id'
        - name: the field's 'name'
        - answer: the answer for that field

        
        1. Determine for each field, if it needs to be filled with user data (not a search field, comment field, etc.).
        2. If a field cannot be filled confidently, use null as the value.
        3. Only fill fields that are relevant to the provided questions and memories in this batch. 

        {{ "form": [{{ "id": "field_id", "name": "field_name", "answer": "field_answer" }}, ...] }}
        If a field cannot be filled confidently, use null as the value.

        Ensure that your response is a valid JSON object.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI assistant that fills out forms based on provided memories and context. Fill out the form fields using the given information and memories. For non-factual or creativity related fields, generate a reasonable response based on the context."},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            filled_fields = Utils.extractValidJson(response.choices[0].message.content)
            return filled_fields['form']
        except Exception as e:
            print(f'Error: {e}. Using an empty dictionary instead.')
            return []
