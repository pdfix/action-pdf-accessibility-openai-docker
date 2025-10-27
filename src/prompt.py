import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from pdfixsdk import PdsStructElement, PdsStructTree, kPdsStructChildElement

from exceptions import ArgumentUnknownCommandException
from pdf_tag_group import PdfTagGroup


class PromptCreator:
    MAX_PROMPT_LENGT: int = 4000
    IDEAL_PROMPT_LENGT: int = 300

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
        self.group: Optional[PdfTagGroup] = None

    def add_surrounding(self, group: PdfTagGroup) -> None:
        """
        Saves surrounding of tag to be able to craft better prompt

        Args:
            group (PdfTagGroup): Surrounding tags around tag that will be processed.
        """
        self.group = group

    def craft_prompt(self) -> str:
        """
        Use all available information to craft prompt for OpenAI.

        Returns:
            Crafted message for chatbot that should contain all information without image itself.
        """
        prompt: str = self._get_the_prompt()
        if self.group:
            prompt += f"\n{self._craft_json_of_surrounding_tags(self.group)}"

        return prompt

    def _get_the_prompt(self) -> str:
        """
        Returns the prompt based on the subcommand and whether it is XML or not.
        """
        if self._is_path(self.path_or_prompt):
            prompt_path: Path = Path(self.path_or_prompt).resolve()
            prompt: str = self._extract_prompt_from_file(prompt_path)
        elif self.path_or_prompt:
            prompt = self._filter_prompt_placeholders(self.path_or_prompt, keep={"lang", "math_ml_version"})
        else:
            prompt = self._get_default_prompt()

        return prompt

    def _is_path(self, path: str) -> bool:
        """
        Checks if the provided path is a valid file path.

        Returns:
            bool: True if the path is a valid file, False otherwise.
        """
        return os.path.isfile(path) if path else False

    def _get_default_prompt(self) -> str:
        """
        Returns the default prompt based on the subcommand and whether it is XML or not.

        Returns:
            str: The default prompt string.
        """
        if self.group:
            if self.subcommand == "generate-alt-text":
                prompt_file: str = (
                    "generate-alt-text-xml-with-surround-tags-prompt.txt"
                    if self.is_xml
                    else "generate-alt-text-with-surround-tags-prompt.txt"
                )
                prompt_path: Path = Path(__file__).parent.joinpath(f"../prompts/{prompt_file}").resolve()
            elif self.subcommand == "generate-table-summary":
                prompt_path = (
                    Path(__file__)
                    .parent.joinpath("../prompts/generate-table-summary-with-surround-tags-prompt.txt")
                    .resolve()
                )
            elif self.subcommand == "generate-mathml":
                prompt_path = (
                    Path(__file__).parent.joinpath("../prompts/generate-mathml-with-surround-tags-prompt.txt").resolve()
                )
            else:
                raise ArgumentUnknownCommandException(self.subcommand)
        else:
            if self.subcommand == "generate-alt-text":
                prompt_file = "generate-alt-text-xml-prompt.txt" if self.is_xml else "generate-alt-text-prompt.txt"
                prompt_path = Path(__file__).parent.joinpath(f"../prompts/{prompt_file}").resolve()
            elif self.subcommand == "generate-table-summary":
                prompt_path = Path(__file__).parent.joinpath("../prompts/generate-table-summary-prompt.txt").resolve()
            elif self.subcommand == "generate-mathml":
                prompt_path = Path(__file__).parent.joinpath("../prompts/generate-mathml-prompt.txt").resolve()
            else:
                raise ArgumentUnknownCommandException(self.subcommand)

        return self._extract_prompt_from_file(prompt_path)

    def _extract_prompt_from_file(self, path: Path) -> str:
        """
        Extracts the prompt from the file at the given path.

        Args:
            path (Path): Path to the prompt file.
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

        def replacer(match: re.Match[str]) -> str:
            var_name: str | Any = match.group(1)
            return match.group(0) if var_name in keep else ""

        return re.sub(r"\{([^}]+)\}", replacer, prompt)

    def _craft_json_of_surrounding_tags(self, group: PdfTagGroup) -> str:
        """
        Takes data about tags around and puts them to json for AI.

        Args:
            group (PdfTagGroup): Surrounding tags around tag that will be processed.

        Returns:
            Json as string for AI about around tags.
        """
        tags_list: list = []

        max_tag_characters: int = int(self.MAX_PROMPT_LENGT / 2 / len(group.tags))

        for index, element in enumerate(group.tags):
            tag_dict: dict = {}
            category: str = element.GetType(False)
            if index == group.target_index:
                tag_dict[category] = f"This is position of {category} that you are generating."
            else:
                tag_dict[category] = self._craft_text_for_element(category, element, max_tag_characters)
            tags_list.append(tag_dict)

        return json.dumps(tags_list, indent=1)

    def _craft_text_for_element(self, category: str, element: PdsStructElement, max_tag_characters: int) -> str:
        """
        For each tag type decide what kind of text helps AI best.

        Args:
            category (str): Tag type.
            element (PdsStructElement): Tag.
            max_tag_characters (int): Max length of message.

        Returns:
            Text that AI will see about this tag.
        """
        match category:
            case "Figure":
                return element.GetAlt()[:max_tag_characters]
            case "Formula":
                return element.GetAlt()[:max_tag_characters]
            case "L":
                return self._craft_structure_from_list(element, max_tag_characters)
            case "P":
                return element.GetActualText()[:max_tag_characters]
            case "Table":
                return self._craft_structure_from_table(element, max_tag_characters)
            case _:
                return element.GetActualText()[:max_tag_characters]

    def _extract_table_rows(self, element: PdsStructElement) -> list[PdsStructElement]:
        """
        From Table element extract all TR elements for futher processing.

        Args:
            element (PdsStructElement): Table element.

        Result:
            Returns list of all TRs from table.
        """
        result: list[PdsStructElement] = []
        count: int = element.GetNumChildren()
        structure_tree: PdsStructTree = element.GetStructTree()
        for i in range(0, count):
            if element.GetChildType(i) != kPdsStructChildElement:
                continue

            child_element: PdsStructElement = structure_tree.GetStructElementFromObject(element.GetChildObject(i))
            match child_element.GetType(False):
                case "THead":
                    grand_count: int = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        grandchild_element: PdsStructElement = structure_tree.GetStructElementFromObject(
                            child_element.GetChildObject(j)
                        )
                        if grandchild_element.GetType(False) == "TR":
                            result.append(grandchild_element)

                case "TR":
                    result.append(child_element)

                case "TBody":
                    grand_count = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        grandchild_element = structure_tree.GetStructElementFromObject(child_element.GetChildObject(j))
                        if grandchild_element.GetType(False) == "TR":
                            result.append(grandchild_element)

                case _:
                    # All other elements are ignore at they should not be there
                    pass

        return result

    def _craft_structure_from_table(self, element: PdsStructElement, max_characters: int) -> str:
        """
        Take Table element and return simplified JSON representation of it.

        Args:
            element (PdsStructElement): Table element.
            max_characters (int): Longest string that will be accepted.

        Result:
            JSON structure in form of string.
        """
        data: list[list[str]] = []
        structure_tree: PdsStructTree = element.GetStructTree()
        rows: list[PdsStructElement] = self._extract_table_rows(element)

        for row in rows:
            cells: list[str] = []
            count: int = row.GetNumChildren()
            for i in range(0, count):
                if row.GetChildType(i) != kPdsStructChildElement:
                    continue
                cell_element: PdsStructElement = structure_tree.GetStructElementFromObject(row.GetChildObject(i))
                match cell_element.GetType(False):
                    case "TH":
                        # Only checking first element for simplification
                        if cell_element.GetNumChildren() > 0 and cell_element.GetChildType(0) != kPdsStructChildElement:
                            content_element: PdsStructElement = structure_tree.GetStructElementFromObject(
                                cell_element.GetChildObject(0)
                            )
                            match content_element.GetType(False):
                                case "P":
                                    cells.append(content_element.GetActualText())
                                case "L":
                                    pass  # list inside cell
                                case "Table":
                                    pass  # nested table inside cell
                                case "Figure":
                                    pass  # figure inside cell
                                case "Lbl":
                                    pass  # label
                                case "Span":
                                    pass  # inline text runs
                                case _:
                                    pass
                    case "TD":
                        # Only checking first element for simplification
                        if cell_element.GetNumChildren() > 0 and cell_element.GetChildType(0) != kPdsStructChildElement:
                            content_element = structure_tree.GetStructElementFromObject(cell_element.GetChildObject(0))
                            match content_element.GetType(False):
                                case "P":
                                    cells.append(content_element.GetActualText())
                                case "L":
                                    pass  # list inside cell
                                case "Table":
                                    pass  # nested table inside cell
                                case "Figure":
                                    pass  # figure inside cell
                                case "Lbl":
                                    pass  # label
                                case "Span":
                                    pass  # inline text runs
                                case _:
                                    pass
                    case _:
                        pass
            data.append(cells)

        data = self._shorten_data(data, max_characters)

        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    def _extract_list_lines(self, element: PdsStructElement) -> list[PdsStructElement]:
        """
        From List element extract all LBody elements for futher processing.

        Args:
            element (PdsStructElement): List element.

        Result:
            Returns list of all LBodies from table.
        """
        result: list[PdsStructElement] = []
        count: int = element.GetNumChildren()
        structure_tree: PdsStructTree = element.GetStructTree()
        for i in range(0, count):
            if element.GetChildType(i) != kPdsStructChildElement:
                continue

            child_element: PdsStructElement = structure_tree.GetStructElementFromObject(element.GetChildObject(i))
            match child_element.GetType(False):
                case "LI":
                    grand_count: int = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        grandchild_element: PdsStructElement = structure_tree.GetStructElementFromObject(
                            child_element.GetChildObject(j)
                        )
                        if grandchild_element.GetType(False) == "LBody":
                            result.append(grandchild_element)

                case _:
                    # All other elements are ignore at they should not be there
                    pass

        return result

    def _craft_structure_from_list(self, element: PdsStructElement, max_characters: int) -> str:
        """
        Take List element and return simplified JSON representation of it.

        Args:
            element (PdsStructElement): List element.
            max_characters (int): Longest string that will be accepted.

        Result:
            JSON structure in form of string.
        """
        data: list[str] = []
        structure_tree: PdsStructTree = element.GetStructTree()
        lines: list[PdsStructElement] = self._extract_list_lines(element)

        for line in lines:
            # Only checking first element for simplification
            if line.GetNumChildren() > 0 and line.GetChildType(0) != kPdsStructChildElement:
                content_element: PdsStructElement = structure_tree.GetStructElementFromObject(line.GetChildObject(0))
                match content_element.GetType(False):
                    case "P":
                        data.append(content_element.GetActualText())
                    case "L":
                        pass  # nested list inside line
                    case "Table":
                        pass  # table inside line
                    case "Figure":
                        pass  # figure inside line
                    case "Note":
                        pass  # footnote/annotation inside line
                    case "Quote":
                        pass  # quote
                    case "Span":
                        pass  # inline text runs
                    case "Reference":
                        pass  # reference
                    case _:
                        pass

        data = self._shorten_data(data, max_characters)

        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    def _shorten_data(self, data: Any, max_length: int) -> Any:
        """
        Universal function that ensures no member is longer that specified.

        Args:
            data (Any): Either list of string.
            max_lenght (int): How many characters can be used.

        Returns:
            Changed structure that is under control.
        """
        if isinstance(data, str):
            return data[:max_length]
        if isinstance(data, list):
            count: int = len(data)
            new_max: int = int(max_length / count)
            return [self._shorten_data(member, new_max) for member in data]
