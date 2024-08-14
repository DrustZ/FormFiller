import re
import json
import datetime

class Utils:
    @staticmethod
    def extractValidJson(input_str):
        try:
            return json.loads(input_str)
        except json.JSONDecodeError:
            json_pattern = re.compile(r'.*\{[\S\s]*\}')
            match = json_pattern.search(input_str)
            if match:
                json_str = match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print("Unable to parse the JSON part from the input string.")
                    return None
            else:
                print("No valid JSON part found in the input string.")
                return None

    @staticmethod
    def get_current_timestamp():
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    @staticmethod
    def format_chroma_results(chroma_results):
        formatted_results = []
        num_results = len(chroma_results['ids'][0])
        for i in range(num_results):
            item = {
                'id': chroma_results['ids'][0][i],
                'distance': chroma_results['distances'][0][i] if chroma_results['distances'] else None,
                'metadata': chroma_results['metadatas'][0][i] if chroma_results['metadatas'] else None,
                'document': chroma_results['documents'][0][i] if chroma_results['documents'] else None,
                'embedding': chroma_results['embeddings'][0][i] if chroma_results['embeddings'] else None
            }
            formatted_results.append(item)
        return formatted_results
