import copy
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

    def clone(self) -> "PromptCreator":
        """
        Craft new copy in thread-safe way.

        Returns:
            Full copy of this class.
        """
        return copy.deepcopy(self)

    def add_surrounding(self, group: PdfTagGroup) -> None:
        """
        Saves surrounding of tag to be able to craft better prompt

        Args:
            group (PdfTagGroup): Surrounding tags around tag that will be processed.
        """
        self.group = group

    def craft_prompt(self, lang: str, math_ml_version: str) -> str:
        """
        Use all available information to craft prompt for OpenAI.

        Args:
            lang (str): Language for the response.
            math_ml_version (str): MathML version for the response.

        Returns:
            Crafted message for chatbot that should contain all information without image itself.
        """
        prompt: str = self._get_the_prompt()
        formatted_prompt: str = prompt.format(lang=lang, math_ml_version=math_ml_version)
        if self.group:
            formatted_prompt += f"\n{self._craft_json_of_surrounding_tags(self.group)}"

        return formatted_prompt

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

        if len(group.tags) == 0:
            return "[]"

        max_tag_characters: int = int(self.MAX_PROMPT_LENGT / 2 / len(group.tags))

        for index, element in enumerate(group.tags):
            tag_dict: dict = {}
            category: str = element.GetType(False)
            if index == group.target_index:
                tag_dict[category] = f"This is position of {category} that you are generating text for."
            else:
                tag_dict[category] = self._extract_text_from_element(element, max_tag_characters)
            tags_list.append(tag_dict)

        return json.dumps(tags_list, indent=1)

    def _extract_table_rows(self, element: PdsStructElement) -> list[PdsStructElement]:
        """
        From Table element extract all "TR" elements for futher processing.

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

            child_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                element.GetChildObject(i)
            )
            if child_element is None:
                continue
            match child_element.GetType(False):
                case "THead":
                    grand_count: int = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        if child_element.GetChildType(j) != kPdsStructChildElement:
                            continue
                        grandchild_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                            child_element.GetChildObject(j)
                        )
                        if grandchild_element and grandchild_element.GetType(False) == "TR":
                            result.append(grandchild_element)

                case "TR":
                    result.append(child_element)

                case "TBody":
                    grand_count = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        if child_element.GetChildType(j) != kPdsStructChildElement:
                            continue
                        grandchild_element = structure_tree.GetStructElementFromObject(child_element.GetChildObject(j))
                        if grandchild_element and grandchild_element.GetType(False) == "TR":
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
                cell_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                    row.GetChildObject(i)
                )
                if cell_element is None:
                    continue
                match cell_element.GetType(False):
                    case "TH":
                        cell_text: str = self._extract_cell_text(structure_tree, cell_element, max_characters)
                        if cell_text:
                            cells.append(cell_text)
                            continue
                    case "TD":
                        cell_text = self._extract_cell_text(structure_tree, cell_element, max_characters)
                        if cell_text:
                            cells.append(cell_text)
                            continue
                    case _:
                        pass
            data.append(cells)

        # Shortening each cell maximum characters to fit prompt into character limit
        data = self._shorten_data(data, max_characters)

        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    def _extract_cell_text(
        self, structure_tree: PdsStructTree, cell_element: PdsStructElement, max_characters: int
    ) -> str:
        """
        Extract text from "TH" or "TD" tags.

        Args:
            structure_tree (PdsStructTree): Structure tree.
            element (PdsStructElement): Table element.
            max_characters (int): Longest string that will be accepted.

        Result:
            Cell content as string.
        """
        # Simple Cell
        cell_text: str = cell_element.GetText(max_characters)
        if cell_text:
            return cell_text
        # Complex Cell
        for j in range(0, cell_element.GetNumChildren()):
            if cell_element.GetChildType(j) != kPdsStructChildElement:
                continue
            content_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                cell_element.GetChildObject(0)
            )
            if content_element is None:
                continue
            content: str = self._extract_text_from_element(content_element, max_characters)
            if content:
                return content
        # Default
        return ""

    def _extract_list_lines(self, element: PdsStructElement) -> list[PdsStructElement]:
        """
        From List element extract all "LBody" elements for futher processing.

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

            child_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                element.GetChildObject(i)
            )
            if child_element is None:
                continue
            match child_element.GetType(False):
                case "LI":
                    grand_count: int = child_element.GetNumChildren()
                    for j in range(0, grand_count):
                        if child_element.GetChildType(j) != kPdsStructChildElement:
                            continue
                        grandchild_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                            child_element.GetChildObject(j)
                        )
                        if grandchild_element and grandchild_element.GetType(False) == "LBody":
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
            # Simple list item:
            line_text: str = line.GetText(max_characters)
            if line_text:
                data.append(line_text)
                continue
            # Complex list item:
            for index in range(0, line.GetNumChildren()):
                if line.GetChildType(index) != kPdsStructChildElement:
                    continue
                content_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                    line.GetChildObject(index)
                )
                if content_element is None:
                    continue
                content: str = self._extract_text_from_element(content_element, max_characters)
                if content:
                    data.append(content)

        # Shortening each cell maximum characters to fit prompt into character limit
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
            if count < 1:
                return []
            new_max: int = int(max_length / count)
            return [self._shorten_data(member, new_max) for member in data]

    def _extract_text_from_element(self, element: PdsStructElement, max_characters: int) -> str:
        """
        For given tag extract text for AI.

        Args:
            element (PdsStructElement): Tag.
            max_characters (int): AI has character limitation for prompt.

        Returns:
            Content of tag or something that helps AI understand what is inside.
        """
        match element.GetType(False):
            # case "Annot":
            #     return element.GetText(max_characters)
            # case "Art":
            #     return element.GetText(max_characters)
            # case "Artifact":
            #     return element.GetText(max_characters)
            # case "Aside":
            #     return element.GetText(max_characters)
            # case "BibEntry":
            #     return element.GetText(max_characters)
            # case "BlockQuote":
            #     return element.GetText(max_characters)
            case "Caption":  # DONE
                return element.GetText(max_characters)
            # case "CellMissingHeader":
            #     return element.GetText(max_characters)
            # case "CellSpan":
            #     return element.GetText(max_characters)
            # case "Code":
            #     return element.GetText(max_characters)
            # case "FENote":
            #     return element.GetText(max_characters)
            case "Figure":
                return element.GetAlt()[:max_characters]
            # case "Form":
            #     return element.GetText(max_characters)
            # case "Formula":
            #     return element.GetAlt()[:max_characters]
            case "H":  # DONE
                return element.GetText(max_characters)
            case "H1":  # DONE
                return element.GetText(max_characters)
            case "H2":  # DONE
                return element.GetText(max_characters)
            case "H3":  # DONE
                return element.GetText(max_characters)
            case "H4":  # DONE
                return element.GetText(max_characters)
            case "H5":  # DONE
                return element.GetText(max_characters)
            case "H6":  # DONE
                return element.GetText(max_characters)
            case "H7":  # DONE
                return element.GetText(max_characters)
            case "H8":  # DONE
                return element.GetText(max_characters)
            # case "Index":
            #     return element.GetText(max_characters)
            case "L":
                return self._craft_structure_from_list(element, max_characters)
            # case "LBody":
            #     return element.GetText(max_characters)
            # case "LI":
            #     return element.GetText(max_characters)
            # case "Lbl":
            #     return element.GetText(max_characters)
            # case "Link":
            #     return element.GetText(max_characters)
            # case "Note":
            #     return element.GetText(max_characters)
            case "P":  # DONE
                return element.GetText(max_characters)
            # case "Quote":
            #     return element.GetText(max_characters)
            # case "Reference":
            #     return element.GetText(max_characters)
            # case "Ruby":
            #     return element.GetText(max_characters)
            # case "Span":
            #     return element.GetText(max_characters)
            # case "TBody":
            #     return element.GetText(max_characters)
            # case "TD":
            #     return element.GetText(max_characters)
            # case "TFoot":
            #     return element.GetText(max_characters)
            # case "TH":
            #     return element.GetText(max_characters)
            # case "THead":
            #     return element.GetText(max_characters)
            # case "TOC":
            #     return element.GetText(max_characters)
            # case "TOCI":
            #     return element.GetText(max_characters)
            # case "TR":
            #     return element.GetText(max_characters)
            case "Table":
                return self._craft_structure_from_table(element, max_characters)
            # case "Title":
            #     return element.GetText(max_characters)
            case _:
                debug_text: str = f"For '{element.GetType(False)}' Tag:"
                debug_text += f"\nalt text: {element.GetAlt()}"
                debug_text += f"\nactual text: {element.GetActualText()}"
                debug_text += f"\ntext: {element.GetText(max_characters)}"
                debug_text += f"\ntitle: {element.GetTitle()}"
                print(debug_text)
                return ""
