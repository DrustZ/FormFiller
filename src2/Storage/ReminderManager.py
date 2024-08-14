import os
import json
import pandas as pd
from datetime import datetime
from openai import OpenAI
import chromadb
import chromadb.utils.embedding_functions as embedding_functions

class ReminderManager:
    def __init__(self, api_key, collection_name="reminders", db_path="chromaDB"):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(collection_name, embedding_function=self.openai_ef)

    def add_reminder(self, content):
        reminder_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{content[:10]}"
        metadata = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self.collection.add(
            ids=[reminder_id],
            documents=[content],
            metadatas=[metadata]
        )
        print(f"Added new reminder: {reminder_id}")
        return reminder_id

    def update_reminder(self, reminder_id, new_content=None):
        existing = self.collection.get(ids=[reminder_id])
        if not existing['ids']:
            print(f"Reminder with ID {reminder_id} not found.")
            return False

        metadata = existing['metadatas'][0]
        content = existing['documents'][0]

        if new_content:
            content = new_content

        metadata['last_updated'] = datetime.now().isoformat()

        self.collection.update(
            ids=[reminder_id],
            documents=[content],
            metadatas=[metadata]
        )
        print(f"Updated reminder: {reminder_id}")
        return True

    def delete_reminder(self, reminder_id):
        try:
            self.collection.delete(ids=[reminder_id])
            print(f"Deleted reminder with ID: {reminder_id}")
            return True
        except Exception as e:
            print(f"Error deleting reminder: {e}")
            return False

    def find_reminders(self, query, n_results=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['metadatas', 'documents', 'distances']
        )
        
        df = pd.DataFrame({
            'ID': results['ids'][0],
            'Content': results['documents'][0],
            'Relevance': results['distances'][0]
        })
        
        return df.sort_values('Relevance')

    def get_all_reminders(self):
        results = self.collection.get(
            include=['metadatas', 'documents']
        )

        df = pd.DataFrame({
            'ID': results['ids'],
            'Content': results['documents'],
            'Created At': [m['created_at'] for m in results['metadatas']],
            'Last Updated': [m['last_updated'] for m in results['metadatas']]
        })

        return df
    
    def delete_all_reminders(self):
        all_ids = self.collection.get()['ids']
        self.collection.delete(ids=all_ids)
        print(f"Deleted {len(all_ids)} reminders from collection")