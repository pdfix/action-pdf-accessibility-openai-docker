import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai.types.chat.chat_completion import Choice
from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdsObject,
    PdsStructElement,
    PdsStructTree,
    kSaveFull,
)

from ai import openai_prompt_with_image
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
    create_groups_of_tags_recursively,
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
    """
    Processes a PDF document by opening it, checking for a structure tree, and recursively
    browsing through the structure elements to process elements that match the specified tags.

    Description:
    This function initializes the Pdfix library and authorizes it using the provided license
    name and key. It then opens the specified input PDF file and checks if the document has a
    structure tree. If the structure tree is present, it starts browsing through the structure
    elements from the root element and processes elements and their surrounding that match
    the specified tags using the `create_groups_of_tags_recursively` function. Finally,
    it saves the processed PDF to the specified output file.

    Args:
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        license_name (str): PDFix license name.
        license_key (str): PDFix license key.
        openai_key (str): OpenAI API key.
        input_path (str): Path to the input PDF file.
        output_path (str): Path to the output PDF file.
        model (str): OpenAI model.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
        regex_tag (str): Regular expression for matching tags that should be processed.
        prompt_creator (PromptCreator): Prompt creator for OpenAI.
        surround_tags_count (int): Number of surrounding tags to include for context.
    """
    pdfix: Optional[Pdfix] = GetPdfix()
    if pdfix is None:
        raise PdfixInitializeException()

    authorize_sdk(pdfix, license_name, license_key)

    # Open doc
    doc: Optional[PdfDoc] = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise PdfixFailedToOpenException(pdfix, input_path)

    struct_tree: Optional[PdsStructTree] = doc.GetStructTree()
    if struct_tree is None:
        raise PdfixNoTagsException(pdfix)

    child_object: Optional[PdsObject] = struct_tree.GetChildObject(0)
    if child_object is None:
        raise PdfixNoTagsException(pdfix)

    child_element: Optional[PdsStructElement] = struct_tree.GetStructElementFromObject(child_object)
    if child_element is None:
        raise PdfixNoTagsException(pdfix)

    groups: list[PdfTagGroup] = create_groups_of_tags_recursively(child_element, regex_tag, surround_tags_count)
    try:
        # Process first group if there is openai authentication error
        process_struct_element(
            pdfix, groups[0], subcommand, openai_key, model, lang, mathml_version, overwrite, prompt_creator
        )
    except OpenAIAuthenticationException:
        raise
    except Exception:
        pass
    # for group in groups:
    #     process_struct_element(pdfix, group, subcommand, openai_key, model, lang, mathml_version, overwrite,
    #         prompt_creator)
    exception: Optional[OpenAIAuthenticationException] = None
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                process_struct_element,
                pdfix,
                group,
                subcommand,
                openai_key,
                model,
                lang,
                mathml_version,
                overwrite,
                prompt_creator,
            )
            # Skip first group as it was already processed
            for group in groups[1:]
        ]
    for future in futures:
        try:
            # Wait for completion and catch exceptions
            future.result()
        except OpenAIAuthenticationException as e:
            # Let other threads finish before throwing exception up
            exception = e
        except Exception:
            pass

    if exception:
        raise exception

    if not doc.Save(output_path, kSaveFull):
        raise PdfixFailedToSaveException(pdfix, output_path)


def process_struct_element(
    pdfix: Pdfix,
    group: PdfTagGroup,
    subcommand: str,
    openai_key: str,
    model: str,
    lang: str,
    math_ml_version: str,
    overwrite: bool,
    prompt_creator: PromptCreator,
) -> None:
    """
    Processes a structure element in a PDF document by generating alternate text or table
    summary using OpenAI.

    Description:
    This function processes a structure element in a PDF document by generating alternate
    text or table summary using OpenAI. It retrieves the element's object ID, type, and
    page number. If the element's bounding box is valid, it renders the page and sends the
    image data to OpenAI for generating alternate text. Depending on the subparser command,
    it either sets the alternate text for the element or updates the table summary attribute.

    Args:
        pdfix (Pdfix): Pdfix SDK.
        group (PdfTagGroup): The structure containing list of structure elements and index of one to process.
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
        prompt_creator (PromptCreator): Prompt creator for OpenAI.
    """
    try:
        element: PdsStructElement = group.tags[group.target_index]
        struct_tree: PdsStructTree = element.GetStructTree()
        document: PdfDoc = struct_tree.GetDoc()
        element_object_id: int = element.GetObject().GetId()
        element_id: str = element.GetId()
        element_type: str = element.GetType(False)
        # element_type_mapped = elem.GetType(True)

        page_num: int = element.GetPageNumber(0)
        if page_num == -1:
            for index in range(0, element.GetNumChildren()):
                page_num = element.GetChildPageNumber(index)
                if page_num != -1:
                    break

        id: str = f"{element_type} [obj: {element_object_id}, id: {element_id}]"

        # get the object page number (it may be written in child objects)
        if page_num == -1:
            logger.info(f"Skipping [{id}] tag that matches the search criteria but can't determine the page number")
            return

        id = f"{element_type} [obj: {element_object_id}, id: {element_id}, page: {page_num + 1}]"

        # get image bbox
        bbox: PdfRect = PdfRect()
        for index in range(element.GetNumPages()):
            page_number: int = element.GetPageNumber(index)
            bbox = element.GetBBox(page_number)
            break

        # check bounding box
        if bbox.left == bbox.right or bbox.top == bbox.bottom:
            logger.info(f"Skipping [{id}] tag that matches the search criteria but can't determine the bounding box")
            return

        logger.info((f"Processing {id} tag matches the search criteria ..."))

        if subcommand == "generate-alt-text":
            orginal_alternate_text: str = element.GetAlt()
            if not overwrite and orginal_alternate_text:
                logger.info(f"Alternate text already exists for {id}")
                return
        elif subcommand == "generate-table-summary":
            if check_if_table_summary_exists(element):
                logger.info(f"Table summary already exists for {id}")
                return
        # elif subcommand == "generate-mathml":
        #   if element.GetDictionary("AF"):
        #       logger.info((f"MathML already exists for {id}"))
        #       return

        data: bytearray = render_page(pdfix, document, page_num, bbox, 1)
        base64_image: str = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

        # with open(img, "wb") as bf:
        #     bf.write(data)

        logger.info(f"Talking to OpenAI for {id} ...")
        prompt: PromptCreator = prompt_creator.clone()
        prompt.add_surrounding(group)
        response: Choice = openai_prompt_with_image(base64_image, openai_key, model, lang, math_ml_version, prompt)

        content: Optional[str] = response.message.content
        if not content:
            logger.info(f"No text generated for {id}")
            return

        if subcommand == "generate-alt-text":
            set_alternate_text(element, content)
            logger.info(f"Alternate text set for {id} tag")
        elif subcommand == "generate-table-summary":
            set_table_summary(element, content)
            logger.info(f"Table summary set for {id} tag")
        elif subcommand == "generate-mathml":
            content = add_mathml_metadata(content)
            set_associated_file_math_ml(element, content, math_ml_version)
            logger.info(f"MathML set for {id} tag")
        else:
            raise ArgumentUnknownCommandException(subcommand)

    except OpenAIAuthenticationException:
        raise
    except ExpectedException as ee:
        # Write error and continue to other element
        logger.exception(f"Expected exception for [{id}]: {str(ee)}")
    except Exception as e:
        # Write error and continue to other element
        logger.exception(f"Unexpected exception for [{id}]: {str(e)}")
