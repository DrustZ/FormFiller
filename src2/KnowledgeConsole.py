import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from Memory import MemoryManager
from Preprocess import Preprocessor

# Load the .env file
load_dotenv()

class ConsoleInterface:
    def __init__(self, memory_manager, preprocessor):
        self.console = Console()
        self.memory_manager = memory_manager
        self.preprocessor = preprocessor

    def display_help(self):
        table = Table(title="Knowledge Base Updater Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_row("file <path> <comment>", "Upload and process a file")
        table.add_row("update <info>", "Directly update knowledge base")
        table.add_row("search <query>", "Search the knowledge base")
        table.add_row("all", "Display all memories")
        table.add_row("del <query>", "Delete a memory")
        table.add_row("help", "Display this help message")
        table.add_row("exit", "Exit the program")
        self.console.print(table)

    def process_file_command(self, command, interactive=True):
        split_res = command.split(maxsplit=1)
        if len(split_res) == 1:
            file_path = command
            comment = os.path.basename(file_path)
        else:
            file_path, comment = split_res
        
        self.console.print(f"Processing file: {file_path} with comment: {comment}")
        content = self.preprocessor.extract_knowledge(file_path, comment)
        
        # Split content into batches
        batches = self.preprocessor.split_content(content)
        
        for i, batch in enumerate(batches):
            self.console.print(f"[cyan]Processing batch {i+1} of {len(batches)}[/cyan]")
            knowledges = self.memory_manager.generate_knowledges(batch, f"name: {comment} - Part {i+1}")
            
            if not interactive:
                self.memory_manager.add_new_facts(knowledges)
                self.console.print("[green]Updated knowledge base with all batches.[/green]")
                continue

            self.console.print("[cyan]Generated knowledges:[/cyan]")
            for knowledge in knowledges:
                self.console.print(f"[green]- {knowledge}[/green]")
                        
            answer = self.console.input("Do you want to update with this batch? (y/n/all/stop): ")
            if answer.lower() == 'y':
                self.memory_manager.add_new_facts(knowledges)
                self.console.print("[green]Updated knowledge base with this batch.[/green]")
            elif answer.lower() == 'all':
                self.memory_manager.add_new_facts(knowledges)
                for remaining_batch in batches[i+1:]:
                    remaining_knowledges = self.memory_manager.generate_knowledges(remaining_batch, f"name: {comment} - Continuation")
                    self.memory_manager.add_new_facts(remaining_knowledges)
                self.console.print("[green]Updated knowledge base with all remaining batches.[/green]")
                break
            elif answer.lower() == 'stop':
                self.console.print("[yellow]File processing stopped.[/yellow]")
                break
            elif answer.lower() == 'n':
                self.console.print("[yellow]Skipped this batch.[/yellow]")
            else:
                self.console.print("[red]Invalid input. Skipping this batch.[/red]")

        self.console.print("[green]File processing complete.[/green]")

    def process_update_command(self, info):
        self.memory_manager.add_new_fact(info)
        self.console.print("[green]Updated knowledge base.[/green]")

    def process_search_command(self, query):
        with self.console.status("[cyan]Searching knowledge base...[/cyan]"):
            results = self.memory_manager.search_memories(query)
        if not results.empty:
            table = Table(title=f"Search Results for '{query}'")
            table.add_column("ID", style="cyan")
            table.add_column("Content", style="green")
            table.add_column("Metadata", style="yellow")
            table.add_column("Distance", style="magenta")
            for _, row in results.iterrows():
                table.add_row(str(row['id']), Text(row['document'], overflow="fold"), Text(row['metadata'], overflow="fold"), f"{row['distance']:.4f}")
            self.console.print(table)
        else:
            self.console.print("[yellow]No results found.[/yellow]")

    def process_all_command(self):
        with self.console.status("[cyan]Fetching all memories...[/cyan]"):
            memories = self.memory_manager.get_all_memories()
        if not memories.empty:
            for _, row in memories.iterrows():
                table = Table(title=f"Memory ID: {row['ID']}", show_header=False, show_lines=True)
                table.add_column(style="cyan")
                table.add_column(style="green")
                table.add_row("Content", Text(row['Document'], overflow="fold"))
                table.add_row("Metadata", Text(row['Metadata'], overflow="fold"))
                self.console.print(table)
                self.console.print("---" * 30)  # Add a dashed line between memories
        else:
            self.console.print("[yellow]No memories found.[/yellow]")

    def process_del_id_command(self, id):
        if self.memory_manager.delete_entry(id):
            self.console.print(f"[green]Successfully deleted memory with ID: {id}[/green]")
        else:
            self.console.print(f"[red]Failed to delete memory with ID: {id}[/red]")

    def process_view_id_command(self, id):
        memory = self.memory_manager.get_memory_by_id(id)
        if memory:
            table = Table(title=f"Memory with ID: {id}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Content", Text(memory['document'], overflow="fold"))
            table.add_row("Metadata", Text(self.memory_manager.format_metadata(memory['metadata']), overflow="fold"))
            self.console.print(table)
        else:
            self.console.print(f"[red]No memory found with ID: {id}[/red]")

    def process_delete_command(self, query):
        with self.console.status("[cyan]Searching for memories to delete...[/cyan]"):
            results = self.memory_manager.search_memories(query, n_results=3)
        if not results.empty:
            self.console.print("[cyan]Found the following memories:[/cyan]")
            for i, (_, row) in enumerate(results.iterrows(), 1):
                self.console.print(f"[green]{i}. ID: {row['id']}[/green]")
                self.console.print(f"   Content: {row['document']}")
                self.console.print(f"   Metadata: {row['metadata']}")
                self.console.print()
            choice = self.console.input("Enter the number of the memory to delete, or 'cancel': ")
            if choice.lower() == 'cancel':
                self.console.print("[yellow]Deletion cancelled.[/yellow]")
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(results):
                        if self.memory_manager.delete_entry(results.iloc[index]['id']):
                            self.console.print("[green]Memory deleted successfully.[/green]")
                        else:
                            self.console.print("[red]Failed to delete memory.[/red]")
                    else:
                        self.console.print("[red]Invalid choice.[/red]")
                except ValueError:
                    self.console.print("[red]Invalid input. Please enter a number or 'cancel'.[/red]")
        else:
            self.console.print("[yellow]No matching memories found.[/yellow]")

    def run(self):
        self.console.print(Panel.fit(
            "[bold cyan]Welcome to the Knowledge Base Updater[/bold cyan]\n"
            "Type [green]help[/green] for a list of commands",
            border_style="blue"
        ))

        while True:
            command = self.console.input("[bold green]Enter a command:[/bold green] ").strip().split(maxsplit=1)
            if command[0] == "exit":
                self.console.print("[yellow]Exiting the Knowledge Base Updater. Goodbye![/yellow]")
                break
            elif command[0] == "help":
                self.display_help()
            elif command[0] == "file" and len(command) == 2:
                self.process_file_command(command[1])
            elif command[0] == "update" and len(command) == 2:
                self.process_update_command(command[1])
            elif command[0] == "search" and len(command) == 2:
                self.process_search_command(command[1])
            elif command[0] == "del_id" and len(command) == 2:
                self.process_del_id_command(command[1])
            elif command[0] == "view_id" and len(command) == 2:
                self.process_view_id_command(command[1])
            elif command[0] == "all":
                self.process_all_command()
            elif command[0] == "del" and len(command) == 2:
                self.process_delete_command(command[1])
            else:
                self.console.print("[red]Invalid command. Type 'help' for a list of commands.[/red]")

def main():
    # Get the API key from the environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        Console().print("[red]Error: OPENAI_API_KEY not found in .env file[/red]")
        return
    memory_manager = MemoryManager(api_key)
    preprocessor = Preprocessor(api_key)
    console_interface = ConsoleInterface(memory_manager, preprocessor)
    console_interface.run()

if __name__ == "__main__":
    main()