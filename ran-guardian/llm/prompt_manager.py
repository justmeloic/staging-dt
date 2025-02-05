"""Prompt Manager module to handle prompt templates"""

import os

current_dir = os.path.dirname(os.path.abspath(__file__))


class PromptManager:
    def __init__(self):
        self.template_dir = os.path.join(current_dir, "prompt_templates")
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        """Load all template files from the template directory."""
        for filename in os.listdir(self.template_dir):
            if filename.endswith(".prompt"):
                template_name = os.path.splitext(filename)[0]
                file_path = os.path.join(self.template_dir, filename)
                with open(file_path, "r", encoding="utf-8") as file:
                    self.templates[template_name] = file.read().strip()

    def get_prompt(self, template_name, **kwargs):
        """
        Retrieve a template and substitute variables.

        Args:
            template_name (str): The name of the template to use (must match filename without the .prompt extension).
            **kwargs: Variables for substitution.

        Returns:
            str: The formatted prompt.

        Raises:
            KeyError: If the template name doesn't exist.
            KeyError: If a required variable is missing.
        """
        if template_name not in self.templates:
            raise KeyError(f"Template '{template_name}' not found")

        template = self.templates[template_name]
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required variable: {e}")

    def get_template(self, template_name: str) -> str:
        """
        Retrieve the prompt template by name (filename without the .prompt extension)

        Returns:
            str: The contents of the prompt template.

        Raises:
            KeyError: If a template with the given name is not found.
        """
        if template_name not in self.templates:
            raise KeyError(f"Template '{template_name}' not found")

        return self.templates[template_name]
