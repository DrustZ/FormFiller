import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print_json
from Memory import MemoryManager
from Preprocess import Preprocessor
from openai import OpenAI
from Util import Utils
import json

load_dotenv()

class FormFillerInterface:
    def __init__(self, openAI_client, memory_manager, preprocessor, debug=False):
        self.console = Console()
        self.memory_manager = memory_manager
        self.preprocessor = preprocessor
        self.client = openAI_client
        self.pdf_cache = {}
        self.question_with_answers = []
        self.debug = debug

    def run(self):
        self.console.print(Panel.fit(
            "[bold cyan]Welcome to the Form Filler Interface[/bold cyan]\n"
            "Type [green]help[/green] for a list of commands",
            border_style="blue"
        ))

        while True:
            command = self.console.input("[bold green]Enter a command:[/bold green] ").strip().split(maxsplit=1)
            if command[0] == "exit":
                break
            elif command[0] == "help":
                self.display_help()
            elif command[0] == "fill" and len(command) == 2:
                self.process_file(command[1])
            else:
                self.console.print("[red]Invalid command. Type 'help' for a list of commands.[/red]")

    def user_continue(self):
        response = self.console.input("Continue? (y/n): ").lower()
        return response == 'y'

    def display_help(self):
        table = Table(title="Form Filler Interface Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_row("fill <path>", "Process and fill a PDF form")
        table.add_row("help", "Display this help message")
        table.add_row("exit", "Exit the program")
        self.console.print(table)

    def process_file(self, command, tmp_file_path="pdfqs.json"):
        split_res = command.split(maxsplit=1)
        if len(split_res) == 1:
            file_path = command
            comment = os.path.basename(file_path)
        else:
            file_path, comment = split_res

        if not os.path.exists(file_path):
            self.console.print(f"[yellow]Warning: File '{file_path}' does not exist.[/yellow]")
            return

        if file_path in self.pdf_cache:
            questions = self.pdf_cache[file_path]
        elif file_path.endswith(".json"):
            with open(file_path, "r") as f:
                questions = json.load(f)
        elif file_path.endswith(".pdf"):
            questions = self.preprocessor.process_pdf_form(file_path, comment)
            self.pdf_cache[file_path] = questions
            with open(tmp_file_path, "w") as f:
                json.dump(questions, f)
        else:
            self.console.print(f"[yellow]Warning: File '{file_path}' is not a PDF or JSON file.[/yellow]")
            return
        
        self.console.print(f'\n[cyan]Questions generated, refer to {tmp_file_path} [/cyan]')
        if not self.user_continue():
            return
        
        q_w_m = self.retrieve_memories_for_questions(questions['questions'])

        if self.debug:
            self.console.print("\n[cyan]Questions with retrieved memories:[/cyan]")
            print_json(data=q_w_m)
            if not self.user_continue():
                return
        
        grouped_batches = self.group_questions_and_memories(q_w_m)
        if self.debug:
            self.console.print("\n[cyan]Grouped batches:[/cyan]")
            print_json(data=grouped_batches)
            if not self.user_continue():
                return

        filled_form = {}
        for i, batch in enumerate(grouped_batches, 1):
            self.console.print(f"\n[cyan]Processing batch {i} of {len(grouped_batches)}[/cyan]")
            batch_filled_form = self.fill_form(batch, comment)
            filled_form.update(batch_filled_form)
            
            # Update q_w_m with the answers
            for question in q_w_m:
                if question['id'] in batch_filled_form:
                    question['answer'] = batch_filled_form[question['id']]
            
            if i < len(grouped_batches):
                continue_processing = self.console.input("Continue to next batch? (y/n): ").lower()
                if continue_processing != 'y':
                    break
        
        self.console.print("\n[green]Form filling complete. Final result:[/green]")
        self.question_with_answers = q_w_m
        self.present_results(q_w_m)

    def retrieve_memories_for_questions(self, questions):
        question_with_memories = []
        for i, item in enumerate(questions):
            memories = self.memory_manager.search_memories(item['question'], n_results=3)
            if not memories.empty:
                question_with_memories.append({
                    "question": item['question'],
                    "field_name": item['field_name'],
                    "id": i, # Use the index as an ID
                    "memories": [
                        {
                            "id": row['id'],
                            "content": row['document'],
                            "metadata": row['metadata'][row['metadata'].find("source_overview"):]
                        }
                        for _, row in memories.iterrows()
                    ]
                })
        return question_with_memories
    
    def group_questions_and_memories(self, questions_with_memories, max_words = 3000):
        def word_count(text: str) -> int:
            return len(text.split())
            
        grouped_batches = []
        current_batch = {"questions": [], "memories": []}
        current_word_count = 0
        current_memory_ids = set()

        for i, item in enumerate(questions_with_memories):
            question_words = word_count(item['question'])
            
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

            item_words = question_words + memory_words

            if current_word_count + item_words > max_words and (
                current_batch["questions"] or current_batch["memories"]):
                
                grouped_batches.append(current_batch)
                current_batch = {"questions": [], "memories": []}
                current_word_count = 0
                current_memory_ids.clear()

            # Add the question
            current_batch["questions"].append({
                "question": item['question'],
                "field_name": item['field_name'],
                "id": item['id']
            })
            
            # Add unique memories
            current_batch["memories"].extend(unique_memories)
            
            current_word_count += item_words

        if current_batch["questions"] or current_batch["memories"]:
            grouped_batches.append(current_batch)

        return grouped_batches
    
    def fill_form(self, batch, user_comment):
        questions = batch["questions"]
        memories = batch["memories"]
        
        prompt = f"""
        Form fields to fill:
        {json.dumps(questions, indent=2)}

        Relevant memories:
        {json.dumps(memories, indent=2)}

        Return a JSON object, with key as 'answer', and value is a list of answers, with each answer corresponding to a question (one key as 'id' of the question, and one key as 'content' of the answer).

        If a field cannot be filled confidently, use null as the value.

        Only fill fields that are relevant to the provided questions and memories in this batch.

        Ensure that your response is a valid JSON object. Here's the user's comment about the form: {user_comment}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI assistant that fills out forms based on provided memories. Each field is reworded into a question, and your answer to the question will be field value. You will answer those question in order, based on the provided memories. For non-factual or creativity related questions (for example, explain a matter, write a report), use the memory to generate a reasonable response in a proper length."},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            filled_form = Utils.extractValidJson(response.choices[0].message.content)
            return {item['id']: item['content'] for item in filled_form['answer']}
        except Exception as e:
            self.console.print(f'[red]Error: {e}. Using an empty dictionary instead.[/red]')
            filled_form = {}
        
        return filled_form

    def present_results(self, q_w_m):
        table = Table(title="Filled Form Results")
        table.add_column("Field", style="cyan")
        table.add_column("Question", style="magenta")
        table.add_column("Answer", style="green")
        
        for question in q_w_m:
            field_name = question['field_name']
            q_text = question['question']
            answer = question.get('answer', 'Not filled')
            
            table.add_row(
                field_name,
                Text(q_text, overflow="fold"),
                Text(str(answer), overflow="fold"),
            )
        
        self.console.print(table)

def main():
    # Get the API key from the environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        Console().print("[red]Error: OPENAI_API_KEY not found in .env file[/red]")
        return
    memory_manager = MemoryManager(api_key)
    preprocessor = Preprocessor(api_key)
    openAI_client = OpenAI(api_key=api_key)
    form_filler = FormFillerInterface(openAI_client, memory_manager, preprocessor)
    form_filler.run()

if __name__ == "__main__":
    main()