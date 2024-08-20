import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from openai import OpenAI
from Storage.ReminderManager import ReminderManager
from Utils.ReminderCommandParser import ReminderCommandParser
from Utils.ReminderResponder import ReminderResponder

# Load environment variables
load_dotenv()

class ReminderConsole:
    def __init__(self):
        self.console = Console()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.console.print("[red]Error: OPENAI_API_KEY not found in .env file[/red]")
            exit(1)

        self.reminder_manager = ReminderManager(api_key)
        self.reminder_responder = ReminderResponder(api_key)
        self.command_parser = ReminderCommandParser(api_key, self.reminder_manager)

    def display_help(self):
        table = Table(title="Reminder Console Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_row("add <reminder content>", "Add a new reminder")
        table.add_row("ask [image_path] <question>", "Ask a question to retrieve reminders (optional image)")
        table.add_row("list", "List all reminders")
        table.add_row("delete <id>", "Delete a reminder by ID")
        table.add_row("help", "Display this help message")
        table.add_row("exit", "Exit the program")
        self.console.print(table)

    def add_reminder(self, content):
        reminder_id = self.reminder_manager.add_reminder(content)
        self.console.print(f"[green]Added reminder with ID: {reminder_id}[/green]")

    def is_valid_image_path(self, path):
        if not os.path.exists(path):
            self.console.print(f"[red]Error: The file '{path}' does not exist.[/red]")
            return False
        if not os.path.isfile(path):
            self.console.print(f"[red]Error: '{path}' is not a file.[/red]")
            return False
        _, ext = os.path.splitext(path)
        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
            self.console.print(f"[red]Error: '{path}' is not a supported image file. Use .jpg, .jpeg, .png, or .gif.[/red]")
            return False
        return True

    def ask_question(self, question, image_path=None):
        description = ''
        if image_path:
            self.console.print(f"[cyan]Using image: {image_path}[/cyan]")
            description, results = self.command_parser.process_command_with_image(question, image_path)
        else:
            results = self.command_parser.process_command(question)
        if results:
            table = Table(title=f"Relevant Reminders for: '{question}'")
            table.add_column("ID", style="cyan")
            table.add_column("Content", style="green")
            table.add_column("Distance", style="magenta")
            for result in results:
                table.add_row(str(result['ID']), result['Content'], f"{result['Relevance']:.4f}")
            self.console.print(table)
            response = self.reminder_responder.generate_response(question, description, results, image_path)
            self.console.print(f"[bold green]Response:[/bold green] {response}")
        else:
            self.console.print("[yellow]No relevant reminders found.[/yellow]")

    def list_reminders(self):
        reminders = self.reminder_manager.get_all_reminders()
        if not reminders.empty:
            table = Table(title="All Reminders")
            table.add_column("ID", style="cyan")
            table.add_column("Content", style="green")
            table.add_column("Created At", style="magenta")
            for _, reminder in reminders.iterrows():
                table.add_row(str(reminder['ID']), reminder['Content'], reminder['Created At'])
            self.console.print(table)
        else:
            self.console.print("[yellow]No reminders found.[/yellow]")

    def delete_reminder(self, reminder_id):
        if self.reminder_manager.delete_reminder(reminder_id):
            self.console.print(f"[green]Successfully deleted reminder with ID: {reminder_id}[/green]")
        else:
            self.console.print(f"[red]Failed to delete reminder with ID: {reminder_id}[/red]")

    def run(self):
        self.console.print(Panel.fit(
            "[bold cyan]Welcome to the Reminder Console[/bold cyan]\n"
            "Type [green]help[/green] for a list of commands",
            border_style="blue"
        ))

        while True:
            command = self.console.input("[bold green]Enter a command:[/bold green] ").strip()
            parts = command.split(maxsplit=2)
            
            if parts[0] == "exit":
                self.console.print("[yellow]Exiting the Reminder Console. Goodbye![/yellow]")
                break
            elif parts[0] == "help":
                self.display_help()
            elif parts[0] == "add" and len(parts) == 3:
                self.add_reminder(parts[1] +' ' +parts[2])
            elif parts[0] == "ask":
                if len(parts) >= 2:
                    potential_image_path = parts[1]
                    if self.is_valid_image_path(potential_image_path):
                        if len(parts) == 3:
                            self.ask_question(parts[2], potential_image_path)
                        else:
                            self.console.print("[red]Invalid 'ask' command. Use: ask <image_path> <question>[/red]")
                    else:
                        # If it's not a valid image path, treat the entire rest as the question
                        self.ask_question(' '.join(parts[1:]))
                else:
                    self.console.print("[red]Invalid 'ask' command. Use: ask [image_path] <question>[/red]")
            elif parts[0] == "list":
                self.list_reminders()
            elif parts[0] == "delete" and len(parts) == 2:
                self.delete_reminder(parts[1])
            else:
                self.console.print("[red]Invalid command. Type 'help' for a list of commands.[/red]")

if __name__ == "__main__":
    reminder_console = ReminderConsole()
    reminder_console.run()