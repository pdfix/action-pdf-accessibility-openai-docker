import base64
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai.types.chat.chat_completion import Choice
from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfRect,
    PdsStructElement,
    PdsStructTree,
    kSaveFull,
)

from ai import openai_prompt_with_image
from exceptions import (
    ArgumentUnknownCommandException,
    ExpectedException,
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
    PdfixNoTagsException,
)
from page_renderer import render_page
from utils import add_mathml_metadata
from utils_sdk import (
    authorize_sdk,
    browse_tags_recursive,
    check_if_table_summary_exists,
    set_alternate_text,
    set_associated_file_math_ml,
    set_table_summary,
)


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
    prompt: str,
) -> None:
    """
    Processes a PDF document by opening it, checking for a structure tree, and recursively
    browsing through the structure elements to process elements that match the specified tags.

    Description:
    This function initializes the Pdfix library and authorizes it using the provided license
    name and key. It then opens the specified input PDF file and checks if the document has a
    structure tree. If the structure tree is present, it starts browsing through the structure
    elements from the root element and processes elements that match the specified tags using
    the `browse_tags_recursive` function. Finally, it saves the processed PDF to the specified
    output file.

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
        prompt (str): Prompt for OpenAI.
    """
    pdfix: Pdfix = GetPdfix()
    if pdfix is None:
        raise PdfixInitializeException()

    authorize_sdk(pdfix, license_name, license_key)

    # Open doc
    doc: PdfDoc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise PdfixFailedToOpenException(pdfix, input_path)

    struct_tree: PdsStructTree = doc.GetStructTree()
    if struct_tree is None:
        raise PdfixNoTagsException(pdfix)

    child_element: PdsStructElement = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        items: list[PdsStructElement] = browse_tags_recursive(child_element, regex_tag)
        # for elem in items:
        #     process_struct_e(elem, subcommand, openai_key, lang, mathml_version, overwrite)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    process_struct_element,
                    pdfix,
                    elem,
                    subcommand,
                    openai_key,
                    model,
                    lang,
                    mathml_version,
                    overwrite,
                    prompt,
                )
                for elem in items
            ]
        for future in futures:
            future.result()  # Wait for completion (optional)
    except Exception:
        raise

    if not doc.Save(output_path, kSaveFull):
        raise PdfixFailedToSaveException(pdfix, output_path)


def process_struct_element(
    pdfix: Pdfix,
    element: PdsStructElement,
    subcommand: str,
    openai_key: str,
    model: str,
    lang: str,
    math_ml_version: str,
    overwrite: bool,
    prompt: str,
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
        element (PdsStructElement): The structure element to process.
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
        prompt (str): Prompt for OpenAI.
    """
    try:
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
            print(f"Skipping [{id}] tag that matches the search criteria but can't determine the page number")
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
            print(f"Skipping [{id}] tag that matches the search criteria but can't determine the bounding box")
            return

        print((f"Processing {id} tag matches the search criteria ..."))

        if subcommand == "generate-alt-text":
            orginal_alternate_text: str = element.GetAlt()
            if not overwrite and orginal_alternate_text:
                print(f"Alternate text already exists for {id}")
                return
        elif subcommand == "generate-table-summary":
            if check_if_table_summary_exists(element):
                print(f"Table summary already exists for {id}")
                return
        # elif subcommand == "generate-mathml":
        #   if element.GetDictionary("AF"):
        #       print((f"MathML already exists for {id}"))
        #       return

        data: bytearray = render_page(pdfix, document, page_num, bbox, 1)
        base64_image: str = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

        # with open(img, "wb") as bf:
        #     bf.write(data)

        print(f"Talking to OpenAI for {id} ...")
        response: Choice = openai_prompt_with_image(base64_image, openai_key, model, lang, math_ml_version, prompt)

        # print(response.message.content)
        content: Optional[str] = response.message.content
        if not content:
            print(f"No alternate text generated for {id}")
            return

        if subcommand == "generate-alt-text":
            set_alternate_text(element, content)
            print(f"Alternate text set for {id} tag")
        elif subcommand == "generate-table-summary":
            set_table_summary(element, content)
            print(f"Table summary set for {id} tag")
        elif subcommand == "generate-mathml":
            content = add_mathml_metadata(content)
            set_associated_file_math_ml(element, content, math_ml_version)
            print(f"MathML set for {id} tag")
        else:
            raise ArgumentUnknownCommandException(subcommand)

    except ExpectedException:
        raise
    except Exception as e:
        # Write error and continue to other element
        print(f"Error: {str(e)}", file=sys.stderr)
