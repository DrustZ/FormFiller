import tornado.ioloop
import tornado.web
import json
from FormFillerConsole import FormFillerInterface
from KnowledgeConsole import ConsoleInterface
from Memory import MemoryManager
from Preprocess import Preprocessor
from openai import OpenAI
from AnalyzeFormHandler import SimplifiedWebFormProcessor
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize components
api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=api_key)
memory_manager = MemoryManager(api_key)
preprocessor = Preprocessor(api_key)
form_filler = FormFillerInterface(openai_client, memory_manager, preprocessor)
knowledge_console = ConsoleInterface(memory_manager, preprocessor)
simplifiedWebFormProcessor = SimplifiedWebFormProcessor(openai_client, memory_manager, form_filler)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Form Filler and Knowledge Base Server")

class UploadDocumentHandler(tornado.web.RequestHandler):
    def post(self):
        files = self.request.files['documents']
        comment = self.get_argument('comment', '')
        for file in files:
            filename = file['filename']
            content = file['body']
            with open(filename, 'wb') as f:
                f.write(content)
            
            knowledge_console.process_file_command(f"{filename} {comment}")
            os.remove(filename)
        self.write({"status": "success", "response": f"Processed {len(files)} documents"})

class AnalyzeFormHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        filled_form = simplifiedWebFormProcessor.process(data)
        self.write({"fieldValues": filled_form})

class ChatHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        message = data['message']
        response = self.process_chat_command(message)
        self.write({"response": response})

    def process_chat_command(self, message):
        command = message.strip().split(maxsplit=1)
        if command[0] == "help":
            return self.get_help_text()
        elif command[0] == "all":
            return self.get_all_memories()
        elif command[0] == "search" and len(command) == 2:
            return self.search_memories(command[1])
        elif command[0] == "update" and len(command) == 2:
            knowledge_console.process_update_command(command[1])
            return "Updated knowledge base."
        elif command[0] == "del_id" and len(command) == 2:
            return self.delete_memory(command[1])
        else:
            return "Invalid command. Type 'help' for a list of commands."

    def get_help_text(self):
        return """
        Available commands:
        - help: Display this help message
        - all: Display all memories
        - search <query>: Search the knowledge base
        - update <info>: Directly update knowledge base
        - del <query>: Delete a memory
        """

    def get_all_memories(self):
        memories = knowledge_console.memory_manager.get_all_memories()
        return memories.to_json(orient='records')

    def search_memories(self, query):
        results = knowledge_console.memory_manager.search_memories(query)
        return results.to_json(orient='records')

    def delete_memory(self, memory_id):
        if knowledge_console.memory_manager.delete_entry(memory_id):
            return f"Deleted memory with ID: {memory_id}"
        return "No matching memory found to delete."

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/analyze-form", AnalyzeFormHandler),
        (r"/upload", UploadDocumentHandler),
        (r"/chat", ChatHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("Server started at http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()
