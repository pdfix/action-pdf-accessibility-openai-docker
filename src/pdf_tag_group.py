from typing import Optional

from pdfixsdk import PdsStructElement, PdsStructTree


class PdfTagGroup:
    """
    Serves as container for list of tags in which one tag is being processed by AI.
    """

    def __init__(self, element: PdsStructElement, target_index: int, tags_for_left: int) -> None:
        """
        Constructing group of PDF Tags around desired tag.

        Args:
            element (PdsStructElement): Parent element from which children are interesting.
            target_index (int): Index of desired tag.
            tags_for_left (int): Number of tags around desired tag from one side.
        """
        self.tags: list[PdsStructElement] = []
        # Mindblowing:
        # - target_ index point event to new list if tags_for_left is same or bigger than target_index
        # - tags_for_left points into position in new list otherwise
        self.target_index: int = min(tags_for_left, target_index)

        structure_tree: PdsStructTree = element.GetStructTree()

        for index in range(element.GetNumChildren()):
            if index < target_index - tags_for_left or index > target_index + tags_for_left:
                continue
            child_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(
                element.GetChildObject(index)
            )
            if child_element:
                self.tags.append(child_element)
