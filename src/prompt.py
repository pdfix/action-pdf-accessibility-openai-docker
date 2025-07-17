import os
import re
from pathlib import Path


class PromptCreator:
    def __init__(self, path_or_prompt: str, subcommand: str, is_xml: bool) -> None:
        """
        Initializes the PromptCreator with a path to a prompt file or prompt itself, subcommand, and whether it is XML.

        Args:
            path (Optional[str]): Path to the prompt file. If None, a default prompt will be used.
            subcommand (str): Subcommand to determine the type of processing.
            is_xml (bool): Whether the prompt is for XML processing.
        """
        self.path_or_prompt: str = path_or_prompt
        self.subcommand: str = subcommand
        self.is_xml: bool = is_xml

    def get_the_prompt(self) -> str:
        """
        Returns the prompt based on the subcommand and whether it is XML or not.
        """
        if self._is_path(self.path_or_prompt):
            prompt = self._extract_prompt_from_file(self.path_or_prompt)
        elif self.path_or_prompt:
            prompt = self._filter_prompt_placeholders(self.path_or_prompt, keep={"lang", "math_ml_version"})
        else:
            prompt = self._get_default_prompt(self.subcommand, self.is_xml)

        return prompt

    def _is_path(self, path: str) -> bool:
        """
        Checks if the provided path is a valid file path.

        Returns:
            bool: True if the path is a valid file, False otherwise.
        """
        return os.path.isfile(path) if path else False

    def _get_default_prompt(self, subcommand: str, is_xml: bool) -> str:
        """
        Returns the default prompt based on the subcommand and whether it is XML or not.

        Args:
            subcommand (str): Subcommand to determine the type of processing.
            is_xml (bool): Whether the prompt is for XML processing.

        Returns:
            str: The default prompt string.
        """
        if subcommand == "generate-alt-text":
            prompt_file = "generate-alt-text-xml-prompt.txt" if is_xml else "generate-alt-text-prompt.txt"
            prompt_path = os.path.join(Path(__file__).parent.absolute(), f"../prompts/{prompt_file}")
        elif subcommand == "generate-table-summary":
            prompt_path = os.path.join(Path(__file__).parent.absolute(), "../prompts/generate-table-summary-prompt.txt")
        elif subcommand == "generate-mathml":
            prompt_path = os.path.join(Path(__file__).parent.absolute(), "../prompts/generate-mathml-prompt.txt")
        else:
            raise ValueError(f"Unknown subparser value {subcommand}")

        return self._extract_prompt_from_file(prompt_path)

    def _extract_prompt_from_file(self, path: str) -> str:
        """
        Extracts the prompt from the file at the given path.

        Args:
            path (str): Path to the prompt file.
        """
        with open(path, "r", encoding="utf-8") as file:
            return self._filter_prompt_placeholders(file.read().strip())

    def _filter_prompt_placeholders(self, prompt: str, keep: set = {"lang", "math_ml_version"}) -> str:
        """
        Removes all placeholders in curly braces from the prompt, except those explicitly listed in `keep`.

        Parameters:
            prompt (str): The original prompt with placeholders like {var}.
            keep (set): A set of placeholder names to keep, without curly braces.

        Returns:
            The cleaned prompt.
        """

        def replacer(match):
            var_name = match.group(1)
            return match.group(0) if var_name in keep else ""

        return re.sub(r"\{([^}]+)\}", replacer, prompt)
