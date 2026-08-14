import base64
import logging
import re
from typing import Optional

from openai.types.chat.chat_completion import Choice
from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdfStructElemEnumProcType,
    PdsObject,
    PdsStructElement,
    PdsStructTree,
    kEnumNone,
    kEnumResultContinue,
    kEnumResultContinueSkip,
    kPdsStructChildElement,
    kSaveFull,
)
from tqdm import tqdm

from ai import openai_prompt_with_image
from constants import PROGRESS_FIRST_STEP, PROGRESS_SECOND_STEP, PROGRESS_THIRD_STEP
from exceptions import (
    ArgumentUnknownCommandException,
    ExpectedException,
    OpenAIAuthenticationException,
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
    PdfixNoTagsException,
)
from logger import get_logger
from page_renderer import render_page
from pdf_tag_group import PdfTagGroup
from prompt import PromptCreator
from utils import add_mathml_metadata
from utils_sdk import (
    authorize_sdk,
    check_if_table_summary_exists,
    set_alternate_text,
    set_associated_file_math_ml,
    set_table_summary,
)

logger: logging.Logger = get_logger()


def process_pdf(
    subcommand: str,
    license_name: Optional[str],
    license_key: Optional[str],
    openai_key: str,
    input_path: str,
    output_path: str,
    model: str,
    lang: str,
    mathml_version: str,
    overwrite: bool,
    regex_tag: str,
    prompt_creator: PromptCreator,
    surround_tags_count: int,
) -> None:
    ProcessPdf(
        subcommand,
        license_name,
        license_key,
        openai_key,
        input_path,
        output_path,
        model,
        lang,
        mathml_version,
        overwrite,
        regex_tag,
        prompt_creator,
        surround_tags_count,
    ).process()


class ProcessPdf:
    """Enumerate and process matching structure elements in a PDF document."""

    def __init__(
        self,
        subcommand: str,
        license_name: Optional[str],
        license_key: Optional[str],
        openai_key: str,
        input_path: str,
        output_path: str,
        model: str,
        lang: str,
        mathml_version: str,
        overwrite: bool,
        regex_tag: str,
        prompt_creator: PromptCreator,
        surround_tags_count: int,
    ) -> None:
        """
        Initialize the ProcessPdf class.

        Args:
            subcommand (str): The subcommand to process.
            license_name (Optional[str]): The license name.
            license_key (Optional[str]): The license key.
            openai_key (str): The OpenAI key.
            input_path (str): The input path.
            output_path (str): The output path.
            model (str): The model to use.
            lang (str): The language to use.
            mathml_version (str): The MathML version to use.
            overwrite (bool): Whether to overwrite existing output.
            regex_tag (str): The regex tag to use.
            prompt_creator (PromptCreator): The prompt creator.
            surround_tags_count (int): The number of tags to surround.
        """
        self.subcommand: str = subcommand
        self.license_name: Optional[str] = license_name
        self.license_key: Optional[str] = license_key
        self.openai_key: str = openai_key
        self.input_path: str = input_path
        self.output_path: str = output_path
        self.model: str = model
        self.lang: str = lang
        self.mathml_version: str = mathml_version
        self.overwrite: bool = overwrite
        self.regex_tag: str = regex_tag
        self.prompt_creator: PromptCreator = prompt_creator
        self.tags_from_left: int = int(surround_tags_count / 2)

        self.pdfix: Optional[Pdfix] = None
        self.doc: Optional[PdfDoc] = None
        self.struct_tree: Optional[PdsStructTree] = None
        self.enumeration_exception: Optional[BaseException] = None

    def process(self) -> None:
        """
        Open, enumerate, update, and save the PDF document.
        """
        total_progress_count: int = PROGRESS_FIRST_STEP + PROGRESS_SECOND_STEP + PROGRESS_THIRD_STEP
        with tqdm(total=total_progress_count) as progress_bar:
            progress_bar.set_description("Initializing")

            self.pdfix = GetPdfix()
            if self.pdfix is None:
                raise PdfixInitializeException()

            authorize_sdk(self.pdfix, self.license_name, self.license_key)

            self.doc = self.pdfix.OpenDoc(self.input_path, "")
            if self.doc is None:
                raise PdfixFailedToOpenException(self.pdfix, self.input_path)

            self.struct_tree = self.doc.GetStructTree()
            if self.struct_tree is None:
                raise PdfixNoTagsException(self.pdfix)

            progress_bar.update(PROGRESS_FIRST_STEP)
            progress_bar.set_description("Processing elements")

            # Keep a local reference so the ctypes callback is not GC'd during enumeration.
            enum_proc = PdfStructElemEnumProcType(self.enumerate_struct_tree)
            try:
                self.doc.EnumStructTree(None, kEnumNone, enum_proc, None)
            finally:
                self.struct_tree = None

            if self.enumeration_exception is not None:
                raise self.enumeration_exception

            # Document needs to be saved even if there is no change.
            progress_bar.n = PROGRESS_FIRST_STEP + PROGRESS_SECOND_STEP
            progress_bar.set_description("Saving document")
            progress_bar.refresh()

            if not self.doc.Save(self.output_path, kSaveFull):
                raise PdfixFailedToSaveException(self.pdfix, self.output_path)

            progress_bar.n = total_progress_count
            progress_bar.set_description("Done")
            progress_bar.refresh()

    def enumerate_struct_tree(self, document_pointer: int, parent_pointer: int, index: int, client_data: int) -> int:
        """
        Process a matching structure element during document enumeration.

        Args:
            document_pointer (int): Document pointer passed by PDFix SDK (unused).
            parent_pointer (int): Parent struct element pointer, or 0 for the root.
            index (int): Child index under the parent.
            client_data (int): Client data pointer passed by PDFix SDK (unused).

        Returns:
            Enumeration result code; always continues to the next element.
        """
        if self.enumeration_exception is not None:
            return kEnumResultContinue

        parent, element = self.resolve_struct_element(parent_pointer, index)
        if parent is None or element is None:
            return kEnumResultContinue

        if not (re.match(self.regex_tag, element.GetType(True)) or re.match(self.regex_tag, element.GetType(False))):
            return kEnumResultContinue

        try:
            group = PdfTagGroup(parent, index, self.tags_from_left)
            self.process_struct_element(group)
        except OpenAIAuthenticationException as exception:
            # ctypes callbacks cannot safely propagate Python exceptions.
            self.enumeration_exception = exception

        # Preserve the previous traversal behavior: matched tags are processed as one unit,
        # so nested structure elements below them are not visited as separate matches.
        return kEnumResultContinueSkip

    def resolve_struct_element(
        self, parent_pointer: int, index: int
    ) -> tuple[Optional[PdsStructElement], Optional[PdsStructElement]]:
        """
        Resolve parent and child elements from enumeration callback arguments.

        Args:
            parent_pointer (int): Parent struct element pointer, or 0 for the root.
            index (int): Child index under the parent.

        Returns:
            Tuple containing parent and child struct elements, or None if the parent or child is not found.
        """
        if self.struct_tree is None:
            return None, None

        parent: PdsStructElement
        if parent_pointer:
            parent = PdsStructElement(parent_pointer)
        else:
            root_object: Optional[PdsObject] = self.struct_tree.GetObject()
            if root_object is None:
                return None, None
            root_element: Optional[PdsStructElement] = self.struct_tree.GetStructElementFromObject(root_object)
            if root_element is None:
                return None, None
            parent = root_element

        if parent.GetChildType(index) != kPdsStructChildElement:
            return parent, None

        child_object: Optional[PdsObject] = parent.GetChildObject(index)
        if child_object is None:
            return parent, None

        return parent, self.struct_tree.GetStructElementFromObject(child_object)

    def process_struct_element(self, group: PdfTagGroup) -> None:
        """
        Generate and apply OpenAI output for one matching structure element.

        Args:
            group (PdfTagGroup): Group of tags to process.
        """
        element_log_id: str = "unknown"
        try:
            element: PdsStructElement = group.tags[group.target_index]
            element_type: str = element.GetType(False)
            element_id: str = element.GetId()
            element_log_id = f"{element_type} [id: {element_id}]"

            # Check overwrite flag
            if self.subcommand == "generate-alt-text":
                original_alternate_text: str = element.GetAlt()
                if not self.overwrite and original_alternate_text:
                    logger.info(f"Alternate text already exists for {element_log_id}")
                    return
            elif self.subcommand == "generate-table-summary":
                if not self.overwrite and check_if_table_summary_exists(element):
                    logger.info(f"Table summary already exists for {element_log_id}")
                    return

            # Check PDFix instance
            if self.pdfix is None:
                return

            struct_tree: Optional[PdsStructTree] = element.GetStructTree()
            if struct_tree is None:
                return
            document: Optional[PdfDoc] = struct_tree.GetDoc()
            if document is None:
                return
            element_obj: Optional[PdsObject] = element.GetObject()
            if element_obj is None:
                return
            element_object_id: int = element_obj.GetId()
            element_log_id = f"{element_type} [obj: {element_object_id}, id: {element_id}]"

            page_num: int = element.GetPageNumber(0)
            if page_num == -1:
                for index in range(0, element.GetNumChildren()):
                    page_num = element.GetChildPageNumber(index)
                    if page_num != -1:
                        break

            # get the object page number (it may be written in child objects)
            if page_num == -1:
                logger.info(
                    f"Skipping [{element_log_id}] tag that matches the search criteria "
                    "but can't determine the page number"
                )
                return

            element_log_id = f"{element_type} [obj: {element_object_id}, id: {element_id}, page: {page_num + 1}]"

            # get image bbox
            bbox: PdfRect = PdfRect()
            for index in range(element.GetNumPages()):
                page_number: int = element.GetPageNumber(index)
                bbox = element.GetBBox(page_number)
                break

            # check bounding box
            if bbox.left == bbox.right or bbox.top == bbox.bottom:
                logger.info(
                    f"Skipping [{element_log_id}] tag that matches the search criteria "
                    "but can't determine the bounding box"
                )
                return

            logger.info(f"Processing {element_log_id} tag matches the search criteria ...")

            data: bytearray = render_page(self.pdfix, document, page_num, bbox, 1)
            base64_image: str = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

            logger.info(f"Talking to OpenAI for {element_log_id} ...")
            prompt: PromptCreator = self.prompt_creator.clone()
            prompt.add_surrounding(group)
            response: Choice = openai_prompt_with_image(
                base64_image,
                self.openai_key,
                self.model,
                self.lang,
                self.mathml_version,
                prompt,
            )

            content: Optional[str] = response.message.content
            if not content:
                logger.info(f"No text generated for {element_log_id}")
                return

            if self.subcommand == "generate-alt-text":
                set_alternate_text(element, content)
                logger.info(f"Alternate text set for {element_log_id} tag")
            elif self.subcommand == "generate-table-summary":
                set_table_summary(element, content)
                logger.info(f"Table summary set for {element_log_id} tag")
            elif self.subcommand == "generate-mathml":
                content = add_mathml_metadata(content)
                set_associated_file_math_ml(element, content, self.mathml_version)
                logger.info(f"MathML set for {element_log_id} tag")
            else:
                raise ArgumentUnknownCommandException(self.subcommand)

        except OpenAIAuthenticationException:
            raise
        except ExpectedException as exception:
            # Write error and continue to other element
            logger.exception(f"Expected exception for [{element_log_id}]: {str(exception)}")
        except Exception as exception:
            # Write error and continue to other element
            logger.exception(f"Unexpected exception for [{element_log_id}]: {str(exception)}")
