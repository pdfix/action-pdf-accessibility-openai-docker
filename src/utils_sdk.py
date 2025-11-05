import ctypes
import re
from typing import Optional

from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdsArray,
    PdsDictionary,
    PdsObject,
    PdsStream,
    PdsStructElement,
    PdsStructTree,
    PsAccountAuthorization,
    kPdsStructChildElement,
)

from exceptions import PdfixActivationException, PdfixAuthorizationException
from pdf_tag_group import PdfTagGroup


def authorize_sdk(pdfix: Pdfix, license_name: Optional[str], license_key: Optional[str]) -> None:
    """
    Tries to authorize or activate Pdfix license.

    Args:
        pdfix (Pdfix): Pdfix sdk instance.
        license_name (string): Pdfix sdk license name (e-mail)
        license_key (string): Pdfix sdk license key
    """
    if license_name and license_key:
        authorization: PsAccountAuthorization = pdfix.GetAccountAuthorization()
        if not authorization.Authorize(license_name, license_key):
            raise PdfixAuthorizationException(pdfix)
    elif license_key:
        if not pdfix.GetStandarsAuthorization().Activate(license_key):
            raise PdfixActivationException(pdfix)
    else:
        print("No license name or key provided. Using PDFix SDK trial")


def create_groups_of_tags_recursively(
    element: PdsStructElement, regex_tag: str, surround_tags_count: int
) -> list[PdfTagGroup]:
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
        element (PdsStructElement): The parent structure element to start browsing from.
        regex_tag (str): The regular expression to match tags.
        surround_tags_count (int): Number of surrounding tags to include for context.
    """
    tags_from_left: int = int(surround_tags_count / 2)
    result: list[PdfTagGroup] = []
    count: int = element.GetNumChildren()
    structure_tree: Optional[PdsStructTree] = element.GetStructTree()
    if structure_tree is None:
        return result

    for i in range(0, count):
        if element.GetChildType(i) != kPdsStructChildElement:
            continue
        child_object: Optional[PdsObject] = element.GetChildObject(i)
        if child_object is None:
            continue
        child_element: Optional[PdsStructElement] = structure_tree.GetStructElementFromObject(child_object)
        if child_element is None:
            continue
        if re.match(regex_tag, child_element.GetType(True)) or re.match(regex_tag, child_element.GetType(False)):
            # process element
            new_group: PdfTagGroup = PdfTagGroup(element, i, tags_from_left)
            result.append(new_group)
        else:
            result.extend(create_groups_of_tags_recursively(child_element, regex_tag, surround_tags_count))
    return result


def set_associated_file_math_ml(element: PdsStructElement, math_ml: str, math_ml_version: str) -> None:
    """
    Set the MathML associated file for a structure element.

    Args:
        element (PdsStructElement): The structure element to set the MathML for.
        math_ml (str): The MathML content to set.
        math_ml_version (str): The MathML version to set.
    """
    # create mathML object
    struct_tree: Optional[PdsStructTree] = element.GetStructTree()
    if struct_tree is None:
        print("Not expected problem with element not retrieving structure tree")
        return
    document: Optional[PdfDoc] = struct_tree.GetDoc()
    if document is None:
        print("Not expected problem with structure tree not retrieving document")
        return
    associated_file_data: Optional[PdsDictionary] = document.CreateDictObject(True)
    if associated_file_data is None:
        print("Not expected problem with document not able to create dictionary")
        return
    associated_file_data.PutName("Type", "Filespec")
    associated_file_data.PutName("AFRelationshhip", "Supplement")
    associated_file_data.PutString("F", math_ml_version)
    associated_file_data.PutString("UF", math_ml_version)
    associated_file_data.PutString("Desc", math_ml_version)

    raw_data: ctypes.Array[ctypes.c_ubyte] = bytearray_to_data(bytearray(math_ml.encode("utf-8")))
    file_dictionary: Optional[PdsDictionary] = document.CreateDictObject(False)
    if file_dictionary is None:
        print("Not expected problem with document not able to create dictionary")
        return
    file_stream: Optional[PdsStream] = document.CreateStreamObject(True, file_dictionary, raw_data, len(math_ml))
    if file_stream is None:
        print("Not expected problem with document not able to create file stream")
        return

    ef_dict: Optional[PdsDictionary] = associated_file_data.PutDict("EF")
    if ef_dict is None:
        print("Not expected problem with dictionary not able to create dictionary")
        return
    ef_dict.Put("F", file_stream)
    ef_dict.Put("UF", file_stream)

    add_associated_file(element, associated_file_data)


def bytearray_to_data(byte_array: bytearray) -> ctypes.Array[ctypes.c_ubyte]:
    """
    Utility function to convert a bytearray to a ctypes array.

    Args:
        byte_array (bytearray): The bytearray to convert.

    Returns:
        The converted ctypes array.
    """
    size: int = len(byte_array)
    return (ctypes.c_ubyte * size).from_buffer(byte_array)


def add_associated_file(element: PdsStructElement, associated_file_data: PdsDictionary) -> None:
    """
    Add an associated file to a structure element.

    Args:
        element (PdsStructElement): The structure element to add the associated file to.
        associated_file_data (PdsDictionary): The associated file data to add.
    """
    element_object: PdsDictionary = PdsDictionary(element.GetObject().obj)
    associated_file_dictionary: Optional[PdsDictionary] = element_object.GetDictionary("AF")
    if associated_file_dictionary:
        # convert dict to an array
        associated_file_array: Optional[PdsArray] = GetPdfix().CreateArrayObject(False)
        if associated_file_array:
            associated_file_array.Put(0, associated_file_dictionary.Clone(False))
            element_object.Put("AF", associated_file_array)

    associated_file_array = element_object.GetArray("AF")
    if not associated_file_array:
        associated_file_array = element_object.PutArray("AF")
    if associated_file_array:
        associated_file_array.Put(associated_file_array.GetNumObjects(), associated_file_data)


def set_alternate_text(element: PdsStructElement, alternate_text: str) -> None:
    """
    Set the alternate text for a structure element.

    Args:
        element (PdsStructElement): The structure element to set the alternate text for.
        alternate_text (str): The alternate text to set.
    """
    element.SetAlt(alternate_text)


def check_if_table_summary_exists(element: PdsStructElement) -> bool:
    """
    Check if a table summary attribute dictionary exists for a structure element.

    Args:
        element (PdsStructElement): The structure element to check.

    Returns:
        True if the table summary attribute dictionary exists, False otherwise.
    """
    attribute_dictionary: Optional[PdsDictionary] = find_table_summary_attribute_dictionary(element)
    return bool(attribute_dictionary and attribute_dictionary.GetString("Summary"))


def set_table_summary(element: PdsStructElement, table_summary: str) -> None:
    """
    Set the table summary attribute for a structure element. If table summary does not exists, create it.

    Args:
        element (PdsStructElement): The structure element to set the table summary for.
        table_summary (str): The table summary to set.
    """
    attribute_dictionary: Optional[PdsDictionary] = find_table_summary_attribute_dictionary(element)

    if not attribute_dictionary:
        struct_tree: Optional[PdsStructTree] = element.GetStructTree()
        if struct_tree is None:
            print("Not expected problem with element not retrieving structure tree")
            return
        document: Optional[PdfDoc] = struct_tree.GetDoc()
        if document is None:
            print("Not expected problem with structure tree not retrieving document")
            return
        attribute_dictionary = document.CreateDictObject(False)
        if attribute_dictionary is None:
            print("Not expected problem with document not able to create dictionary")
            return
        attribute_dictionary.PutName("O", "Table")
        element.AddAttrObj(attribute_dictionary)

    attribute_dictionary.PutString("Summary", table_summary)


def find_table_summary_attribute_dictionary(element: PdsStructElement) -> Optional[PdsDictionary]:
    """
    Find the attribute dictionary for table summary in a structure element.

    Args:
        element (PdsStructElement): The structure element to search for the attribute dictionary.

    Returns:
        The attribute dictionary for table summary, or None if not found.
    """
    for index in reversed(range(element.GetNumAttrObjects())):
        attribute_object: Optional[PdsObject] = element.GetAttrObject(index)
        if not attribute_object:
            continue
        attribute_item: PdsDictionary = PdsDictionary(attribute_object.obj)
        if attribute_item.GetText("O") == "Table":
            return attribute_item
    return None
