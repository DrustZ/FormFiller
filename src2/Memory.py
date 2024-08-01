import os
import re
import json
import pandas as pd
from Util import Utils
from openai import OpenAI
import chromadb
import chromadb.utils.embedding_functions as embedding_functions

class MemoryManager:
    def __init__(self, api_key, collection_name="test", db_path="/Users/mingrui/Documents/Codes/FormFiller/chromaDB"):
        self.api_key = api_key
        self.client = OpenAI()
        
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(collection_name, embedding_function=self.openai_ef)

    def generate_knowledges(self, text, user_metadata='name: Mingrui Zhang'):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": 
                '''
                You are a knowledge generator based on the given text about a user's document. Generate one knowledge of the user's info per line, to be stored in a vector db for future form filling. Only return user-related knowledge, line by line. Exclude document appearance descriptions.

                Do not include knowledge about objectively describe the document itself, such as apperance etc, that wont be used for form filling (which usually only asks for the user's info).
                
                Use the user's name if identifiable. Each line should be fact-based, minimal (knowledge graph style), but contextually sufficient (in a statement way, must contains who, what, when, and extra info, so that even only with that line, the user can understand the context) 
                
                (for example, instead of saying the reference number for the user is xxx, say the reference number of xxx document of the user in year yy is x; or instead of saying "start date of user is x, say the start data of what thing for the user is x). 
                
                For new lines in facts, use a space or comma, since new line is strictly used for separating facts. Use plain text only.
                
                In the last line, provide a brief one phrase document overview, including type and date of the doc if available.
                '''
                },
                {"role": "user", "content": f"Generate knowledges from the text:\n\n{text} \n\n metadata: {user_metadata}"}
            ],
            max_tokens=4000
        )
        return response.choices[0].message.content.strip().split('\n')

    def generate_metadata(self, overview):
        return {
            "created_at": Utils.get_current_timestamp(),
            "last_updated": Utils.get_current_timestamp(),
            "source_overview": overview
        }

    def add_new_facts(self, res):
        res = [r for r in res if len(r.strip()) > 0]
        for r in res[:-1]:
            self.add_or_update_info(r, res[-1])

    def add_new_fact(self, fact):
        self.add_or_update_info(fact)

    def add_or_update_info(self, new_info, new_metadata=''):   
        results = self.collection.query(
            query_texts=[new_info],
            n_results=2,
            include=["metadatas", "documents", "distances"]
        )
        
        formatted_results = Utils.format_chroma_results(results)
        
        for item in formatted_results:
            existing_info = item['document']
            existing_metadata = item['metadata']
            
            result = self.decide_and_merge(existing_info, existing_metadata['source_overview'], new_info, new_metadata)
            
            if result["merge_decision"]:
                existing_metadata['source_overview'] = result["merged_metadata"]
                existing_metadata['last_updated'] = Utils.get_current_timestamp()
                self.collection.update(
                    ids=[item['id']],
                    documents=[result["merged_information"]],
                    metadatas=[existing_metadata]
                )
                print(f"Updated existing entry: {item['id']}")
                print(f"Reason for merge: {result['reason']}")
                return
        
        new_id = f"{Utils.get_current_timestamp()}{new_info[:10]}"
        self.collection.add(
            ids=[new_id],
            documents=[new_info],
            metadatas=[self.generate_metadata(new_metadata)]
        )
        print(f"Added new entry: {new_id}")

    def decide_and_merge(self, existing_info, existing_metadata, new_info, new_metadata):
        prompt = f"""
        Existing information: "{existing_info}"
        Existing metadata: {existing_metadata}
        New information: "{new_info}"
        New metadata: {new_metadata}

        Analyze these entries for form-filling use. Each entry should be unique, concise, yet contextually complete.

        Tasks:
                1. Decide if merging is appropriate (same/newer info). If the overlap on content, you should decide if the extra info is worth a separate entry for the new data based on context and length. 
                If they contains conflict/different content but same meaning, you should decide whether make sense to merge (for example, can be based on metadata, if one says "salary in 2022" is 100k and the other says "salary in 2021" is 100k, then they should be merged, but if one says "salary of student 2021 was 20k and in meta 2024 was 1000k, then maybe not merge").

                2. If merging, provide a combined version (precise, brief, contextually complete so that it helps form filling. For example, instead of saying the reference number for the user is xxx, say the reference number of xxx document of the user in year yy is x).

                3. Don't merge if too lengthy (>100 words) or containing distinct information.

        Use plain text for both information and metadata.

        Provide your response in the following JSON format:
        {{
            "merge_decision": true/false,
            "reason": "short phrase about why merge or not merge: too lengthy, different pieces, same info, newer info, etc.",
            "merged_metadata": "updated metadata if merged, otherwise null",
            "merged_information": "Combined information if merged, otherwise null"
        }}

        Ensure valid JSON with all fields.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with analyzing and merging information. Provide your response in valid JSON format."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()
        print(f'existing={existing_info}\nnew={new_info}\n{result}')
        try:
            return Utils.extractValidJson(result)
        except json.JSONDecodeError:
            return {
                "merge_decision": False,
                "reason": "Failed to parse AI response",
                "merged_metadata": None,
                "merged_information": None
            }

    def format_metadata(self, metadata):
        return '\n'.join([f"{k}: {v}" for k, v in metadata.items()])

    def get_all_memories(self):
        results = self.collection.get(
            include=['metadatas', 'documents']
        )

        df = pd.DataFrame({
            'ID': results['ids'],
            'Document': results['documents'],
            'Metadata': results['metadatas']
        })

        df['Metadata'] = df['Metadata'].apply(self.format_metadata)

        return df

    def search_memories(self, query_text, n_results=5):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=['metadatas', 'documents', 'distances']
        )
        
        formatted_results = Utils.format_chroma_results(results)
        
        df = pd.DataFrame(formatted_results)
        if not df.empty:
            df['metadata'] = df['metadata'].apply(self.format_metadata)
            column_order = ['id', 'distance', 'document', 'metadata']
            df = df.reindex(columns=[col for col in column_order if col in df.columns])
        return df

    def delete_entry(self, entry_id):
        try:
            self.collection.delete(ids=[entry_id])
            print(f"Deleted entry with ID: {entry_id}")
            return True
        except Exception as e:
            print(f"Error deleting entry: {e}")
            return False

    def delete_all_entries(self):
        all_ids = self.collection.get()['ids']
        print(all_ids)
        self.collection.delete(ids=all_ids)
        print(f"Deleted {len(all_ids)} entries from collection ")
