import base64
import ctypes
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    PdfImageParams,
    PdfPageRenderParams,
    PdfRect,
    PdsDictionary,
    PdsStructElement,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kPdsStructChildElement,
    kRotate0,
    kSaveFull,
)

from ai import openai_prompt


# utils
def bytearray_to_data(byte_array: bytearray) -> ctypes.Array[ctypes.c_ubyte]:
    """Utility function to convert a bytearray to a ctypes array."""
    size = len(byte_array)
    return (ctypes.c_ubyte * size).from_buffer(byte_array)


def set_alternate_text(element: PdsStructElement, alternate_text: str) -> None:
    """Set the alternate text for a structure element."""
    element.SetAlt(alternate_text)


def find_table_summary_attribute_dictionary(element: PdsStructElement) -> Optional[PdsDictionary]:
    """Find the attribute dictionary for table summary in a structure element."""
    for index in reversed(range(element.GetNumAttrObjects())):
        attribute_object = element.GetAttrObject(index)
        if not attribute_object:
            continue
        attribute_item = PdsDictionary(attribute_object.obj)
        if attribute_item.GetText("O") == "Table":
            return attribute_item
    return None


def check_if_table_summary_exists(element: PdsStructElement) -> bool:
    """Check if a table summary attribute dictionary exists for a structure element."""
    attribute_dictionary = find_table_summary_attribute_dictionary(element)
    return bool(attribute_dictionary and attribute_dictionary.GetString("Summary"))


def set_table_summary(element: PdsStructElement, table_summary: str) -> None:
    """Set the table summary attribute for a structure element. If table summary does not exists, create it."""
    attribute_dictionary = find_table_summary_attribute_dictionary(element)

    if not attribute_dictionary:
        document = element.GetStructTree().GetDoc()
        attribute_dictionary = document.CreateDictObject(False)
        attribute_dictionary.PutName("O", "Table")
        element.AddAttrObj(attribute_dictionary)

    attribute_dictionary.PutString("Summary", table_summary)


def add_associated_file(element: PdsStructElement, associated_file_data: PdsDictionary) -> None:
    """Add an associated file to a structure element."""
    element_object = PdsDictionary(element.GetObject().obj)
    associated_file_dictionary = element_object.GetDictionary("AF")
    if associated_file_dictionary:
        # convert dict to an array
        associated_file_array = GetPdfix().CreateArrayObject(False)
        associated_file_array.Put(0, associated_file_dictionary.Clone(False))
        element_object.Put("AF", associated_file_array)

    associated_file_array = element_object.GetArray("AF")
    if not associated_file_array:
        associated_file_array = element_object.PutArray("AF")
    associated_file_array.Put(associated_file_array.GetNumObjects(), associated_file_data)


def set_associated_file_math_ml(element: PdsStructElement, math_ml: str, math_ml_version: str) -> None:
    """Set the MathML associated file for a structure element."""
    # create mathML object
    document = element.GetStructTree().GetDoc()
    associated_file_data = document.CreateDictObject(True)
    associated_file_data.PutName("Type", "Filespec")
    associated_file_data.PutName("AFRelationshhip", "Supplement")
    associated_file_data.PutString("F", "mathml-4")  # TODO Jozo ask math_ml_version
    associated_file_data.PutString("UF", "mathml-4")  # TODO Jozo ask  math_ml_version
    associated_file_data.PutString("Desc", "mathml-4")  # TODO Jozo ask  math_ml_version

    raw_data = bytearray_to_data(bytearray(math_ml.encode("utf-8")))
    file_dictionary = document.CreateDictObject(False)
    file_stream = document.CreateStreamObject(True, file_dictionary, raw_data, len(math_ml))

    ef_dict = associated_file_data.PutDict("EF")
    ef_dict.Put("F", file_stream)
    ef_dict.Put("UF", file_stream)

    add_associated_file(element, associated_file_data)


def render_page(doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    """
    Render PDF document page to bytearray image.

    Args:
        doc (PdfDoc): The PDF document to render.
        page_num (int): The page number to render.
        bbox (PdfRect): The bounding box of the page to render.
        zoom (float): The zoom level for rendering.
    Returns:
        The rendered image data as a bytearray.
    """
    page = doc.AcquirePage(page_num)
    try:
        page_view = page.AcquirePageView(zoom, kRotate0)

        try:
            rect = page_view.RectToDevice(bbox)

            # render content
            render_parameters = PdfPageRenderParams()
            render_parameters.matrix = page_view.GetDeviceMatrix()
            render_parameters.clip_box = bbox
            render_parameters.image = GetPdfix().CreateImage(
                rect.right - rect.left,
                rect.bottom - rect.top,
                kImageDIBFormatArgb,
            )

            try:
                page.DrawContent(render_parameters)

                # save image to stream and data
                memory_stream = GetPdfix().CreateMemStream()
                try:
                    image_parameters = PdfImageParams()
                    image_parameters.format = kImageFormatJpg
                    render_parameters.image.SaveToStream(memory_stream, image_parameters)

                    data = bytearray(memory_stream.GetSize())
                    raw_data = (ctypes.c_ubyte * len(data)).from_buffer(data)
                    memory_stream.Read(0, raw_data, len(data))
                except Exception:
                    raise
                finally:
                    memory_stream.Destroy()
            except Exception:
                raise
            finally:
                render_parameters.image.Destroy()
        except Exception:
            raise
        finally:
            page_view.Release()
    except Exception:
        raise
    finally:
        page.Release()

    return data


def process_struct_element(
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
        element (PdsStructElement): The structure element to process.
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        openai_key (str): OpenAI API key.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        overwrite (bool): Whether to overwrite previous alternate text.
    """
    try:
        document = element.GetStructTree().GetDoc()
        element_object_id = element.GetObject().GetId()
        element_id = element.GetId()
        element_type = element.GetType(False)
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

        data = render_page(document, page_num, bbox, 1)
        base64_image = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

        # with open(img, "wb") as bf:
        #     bf.write(data)

        print(f"Talking to OpenAI for {id} ...")
        response = openai_prompt(base64_image, openai_key, subcommand, lang, math_ml_version)

        # print(response.message.content)
        content = response.message.content
        if not content:
            print(f"No alternate text found for {id}")
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
        print(f"Error: {str(e)}")


def browse_tags_recursive(element: PdsStructElement, regex_tag: str) -> list:
    """
    Recursively browses through the structure elements of a PDF document and processes
    elements that match the specified tags.

    Description:
    This function recursively browses through the structure elements of a PDF document
    starting from the specified parent element. It checks each child element to see if it
    matches the specified tags using a regular expression. If a match is found, the element
    is processed using the `process_struct_elem` function. If no match is found, the function
    calls itself recursively on the child element.

    Args:
        elem (PdsStructElement): The parent structure element to start browsing from.
        regex_tag (str): The regular expression to match tags.
    """
    result = []
    count = element.GetNumChildren()
    structure_tree = element.GetStructTree()
    for i in range(0, count):
        if element.GetChildType(i) != kPdsStructChildElement:
            continue
        child_element = structure_tree.GetStructElementFromObject(element.GetChildObject(i))
        if re.match(regex_tag, child_element.GetType(True)) or re.match(regex_tag, child_element.GetType(False)):
            # process element
            result.append(child_element)
        else:
            result.extend(browse_tags_recursive(child_element, regex_tag))
    return result


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

    if license_name and license_key:
        if not pdfix.GetAccountAuthorization().Authorize(license_name, license_key):
            raise Exception(pdfix.GetError())
    elif license_key:
        if not pdfix.GetStandarsAuthorization().Activate(license_key):
            raise Exception(pdfix.GetError())
    else:
        print("No license name or key provided. Using PDFix SDK trial")

    # Open doc
    doc = pdfix.OpenDoc(input, "")
    if doc is None:
        raise Exception(f"Unable to open PDF : {str(pdfix.GetError())}")

    struct_tree = doc.GetStructTree()
    if struct_tree is None:
        raise Exception(f"PDF has no structure tree : {str(pdfix.GetError())}")

    child_element = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        items = browse_tags_recursive(child_element, regex_tag)
        # for elem in items:
        #     process_struct_e(elem, subcommand, openai_key, lang, mathml_version, overwrite)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_struct_element, elem, subcommand, openai_key, lang, mathml_version, overwrite)
                for elem in items
            ]
        for future in futures:
            future.result()  # Wait for completion (optional)
    except Exception as e:
        raise e

    if not doc.Save(output, kSaveFull):
        raise Exception(f"Unable to save PDF : {str(pdfix.GetError())}")
