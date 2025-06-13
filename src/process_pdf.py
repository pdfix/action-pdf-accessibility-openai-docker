import base64
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from pdfixsdk.Pdfix import (
    GetPdfix,
    Pdfix,
    PdfRect,
    PdsStructElement,
    PdsStructTree,
    kSaveFull,
)

from ai import openai_prompt_with_image
from exceptions import PdfixException
from page_renderer import render_page
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
    input: str,
    output: str,
    lang: str,
    mathml_version: str,
    overwrite: bool,
    regex_tag: str,
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
        input (str): Path to the input PDF file.
        output (str): Path to the output PDF file.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
        regex_tag (str): Regular expression for matching tags that should be processed.
    """
    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    authorize_sdk(pdfix, license_name, license_key)

    # Open doc
    doc = pdfix.OpenDoc(input, "")
    if doc is None:
        raise PdfixException(pdfix, "Unable to open PDF")

    struct_tree: PdsStructTree = doc.GetStructTree()
    if struct_tree is None:
        raise PdfixException(pdfix, "PDF has no structure tree")

    child_element = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        items = browse_tags_recursive(child_element, regex_tag)
        # for elem in items:
        #     process_struct_e(elem, subcommand, openai_key, lang, mathml_version, overwrite)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    process_struct_element, pdfix, elem, subcommand, openai_key, lang, mathml_version, overwrite
                )
                for elem in items
            ]
        for future in futures:
            future.result()  # Wait for completion (optional)
    except Exception:
        raise

    if not doc.Save(output, kSaveFull):
        raise PdfixException(pdfix, "Unable to save PDF ")


def process_struct_element(
    pdfix: Pdfix,
    element: PdsStructElement,
    subcommand: str,
    openai_key: str,
    lang: str,
    math_ml_version: str,
    overwrite: bool,
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
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
    """
    try:
        document = element.GetStructTree().GetDoc()
        element_object_id: int = element.GetObject().GetId()
        element_id: str = element.GetId()
        element_type: str = element.GetType(False)
        # element_type_mapped = elem.GetType(True)

        page_num = element.GetPageNumber(0)
        if page_num == -1:
            for i in range(0, element.GetNumChildren()):
                page_num = element.GetChildPageNumber(i)
                if page_num != -1:
                    break

        id = f"{element_type} [obj: {element_object_id}, id: {element_id}]"

        # get the object page number (it may be written in child objects)
        if page_num == -1:
            print(f"Skipping [{id}] tag that matches the search criteria but can't determine the page number")
            return

        id = f"{element_type} [obj: {element_object_id}, id: {element_id}, page: {page_num + 1}]"

        # get image bbox
        bbox = PdfRect()
        for i in range(element.GetNumPages()):
            page_num = element.GetPageNumber(i)
            bbox = element.GetBBox(page_num)
            break

        # check bounding box
        if bbox.left == bbox.right or bbox.top == bbox.bottom:
            print(f"Skipping [{id}] tag that matches the search criteria but can't determine the bounding box")
            return

        print((f"Processing {id} tag matches the search criteria ..."))

        if subcommand == "generate-alt-text":
            orginal_alternate_text = element.GetAlt()
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

        data = render_page(pdfix, document, page_num, bbox, 1)
        base64_image = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

        # with open(img, "wb") as bf:
        #     bf.write(data)

        print(f"Talking to OpenAI for {id} ...")
        response = openai_prompt_with_image(base64_image, openai_key, subcommand, lang, math_ml_version)

        # print(response.message.content)
        content = response.message.content
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
            set_associated_file_math_ml(element, content, math_ml_version)
            print(f"MathML set for {id} tag")
        else:
            print(f"Unknown operation: {subcommand}")

    except Exception as e:
        # Write error and continue to other element
        print(f"Error: {str(e)}", file=sys.stderr)
