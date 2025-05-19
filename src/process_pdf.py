import base64
import ctypes
import re
from concurrent.futures import ThreadPoolExecutor

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

from ai import openai_propmpt


# utils
def bytearray_to_data(byte_array):
    size = len(byte_array)
    return (ctypes.c_ubyte * size).from_buffer(byte_array)


def set_alt_text(elem: PdsStructElement, alt_text: str):
    elem.SetAlt(alt_text)


def get_table_summary(elem: PdsStructElement):
    attr_dict = None
    for index in reversed(range(elem.GetNumAttrObjects())):
        attr_obj = elem.GetAttrObject(index)
        if not attr_obj:
            continue
        attr_item = PdsDictionary(attr_obj.obj)
        if attr_item.GetText("O") == "Table":
            attr_dict = attr_item
            summary = attr_dict.GetString("Summary")
            if summary:
                return True
    return None


def set_table_summary(elem: PdsStructElement, table_summary: str):
    doc = elem.GetStructTree().GetDoc()
    attr_dict = None
    for index in reversed(range(elem.GetNumAttrObjects())):
        attr_obj = elem.GetAttrObject(index)
        if not attr_obj:
            continue
        attr_item = PdsDictionary(attr_obj.obj)
        if attr_item.GetText("O") == "Table":
            attr_dict = attr_item
            break

    if not attr_dict:
        attr_dict = doc.CreateDictObject(False)
        attr_dict.PutName("O", "Table")
        elem.AddAttrObj(attr_dict)

    attr_dict.PutString("Summary", table_summary)


def add_associated_file(elem: PdsStructElement, af: PdsDictionary):
    elem_obj = PdsDictionary(elem.GetObject().obj)
    af_dict = elem_obj.GetDictionary("AF")
    if af_dict:
        # convert dict to an array
        af_arr = GetPdfix().CreateArrayObject(False)
        af_arr.Put(0, af_dict.Clone(False))
        elem_obj.Put("AF", af_arr)

    af_arr = elem_obj.GetArray("AF")
    if not af_arr:
        af_arr = elem_obj.PutArray("AF")
    af_arr.Put(af_arr.GetNumObjects(), af)


def set_af_math_ml(elem: PdsStructElement, mathml: str):
    # create mathML object
    doc = elem.GetStructTree().GetDoc()
    af_dict = doc.CreateDictObject(True)
    af_dict.PutName("Type", "Filespec")
    af_dict.PutName("AFRelationshhip", "Supplement")
    af_dict.PutString("F", "mathml-4")
    af_dict.PutString("UF", "mathml-4")
    af_dict.PutString("Desc", "mathml-4")

    raw_data = bytearray_to_data(bytearray(mathml.encode("utf-8")))
    f_dict = doc.CreateDictObject(False)
    f_stm = doc.CreateStreamObject(True, f_dict, raw_data, len(mathml))

    ef_dict = af_dict.PutDict("EF")
    ef_dict.Put("F", f_stm)
    ef_dict.Put("UF", f_stm)

    add_associated_file(elem, af_dict)


def render_page(doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    page = doc.AcquirePage(page_num)
    page_view = page.AcquirePageView(zoom, kRotate0)

    rect = page_view.RectToDevice(bbox)

    # render content
    render_params = PdfPageRenderParams()
    render_params.matrix = page_view.GetDeviceMatrix()
    render_params.clip_box = bbox
    render_params.image = GetPdfix().CreateImage(
        rect.right - rect.left,
        rect.bottom - rect.top,
        kImageDIBFormatArgb,
    )
    page.DrawContent(render_params)

    # save image to stream and data
    stm = GetPdfix().CreateMemStream()
    img_params = PdfImageParams()
    img_params.format = kImageFormatJpg
    render_params.image.SaveToStream(stm, img_params)

    data = bytearray(stm.GetSize())
    raw_data = (ctypes.c_ubyte * len(data)).from_buffer(data)
    stm.Read(0, raw_data, len(data))

    # cleanup
    stm.Destroy()
    render_params.image.Destroy()
    page_view.Release()
    page.Release()

    return data


def process_struct_elem(elem: PdsStructElement, args):
    """
    Processes a structure element in a PDF document by generating alternate text or table
    summary using OpenAI.

    Arguments:
    - elem (PdsStructElement): The structure element to process.
    - doc (PdfDoc): The PDF document containing the structure element.
    - args (argparse.Namespace): The command-line arguments containing the tags to match,
      overwrite flag, and subparser command.

    Description:
    This function processes a structure element in a PDF document by generating alternate
    text or table summary using OpenAI. It retrieves the element's object ID, type, and
    page number. If the element's bounding box is valid, it renders the page and sends the
    image data to OpenAI for generating alternate text. Depending on the subparser command,
    it either sets the alternate text for the element or updates the table summary attribute.

    Example:
    # Example usage
    process_struct_elem(struct_element, pdf_document, args)
    """
    try:
        doc = elem.GetStructTree().GetDoc()
        elem_obj_id = elem.GetObject().GetId()
        elem_id = elem.GetId()
        elem_type = elem.GetType(False)
        # elem_type_mapped = elem.GetType(True)

        page_num = elem.GetPageNumber(0)
        if page_num == -1:
            for i in range(0, elem.GetNumChildren()):
                page_num = elem.GetChildPageNumber(i)
                if page_num != -1:
                    break

        id = f"{elem_type} [obj: {elem_obj_id}, id: {elem_id}]"

        # get the object page number (it may be written in child objects)
        if page_num == -1:
            print("Skipping [" + id + "] tag that matches the search criteria but can't determine the page number")
            return

        id = f"{elem_type} [obj: {elem_obj_id}, id: {elem_id}, page: {page_num + 1}]"

        # get image bbox
        bbox = PdfRect()
        for i in range(elem.GetNumPages()):
            page_num = elem.GetPageNumber(i)
            bbox = elem.GetBBox(page_num)
            break

        # check bounding box
        if bbox.left == bbox.right or bbox.top == bbox.bottom:
            print("Skipping [" + id + "] tag that matches the search criteria but can't determine the bounding box")
            return

        print((f"Processing {id} tag matches the search criteria ..."))

        if args.command == "generate-alt-text":
            org_alt = elem.GetAlt()
            if not args.overwrite and org_alt:
                print((f"Alt text already exists for {id}"))
                return
        elif args.command == "generate-table-summary":
            if get_table_summary(elem):
                print((f"Table summary already exists for {id}"))
                return
        # elif args.subparser == "generate-mathml":
        #   if elem.GetDictionary("AF"):
        #       print((f"MathML already exists for {id}"))
        #       return

        data = render_page(doc, page_num, bbox, 1)
        base64_image = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"

        # with open(img, "wb") as bf:
        #     bf.write(data)

        print((f"Talking to OpenAI for {id} ..."))
        response = openai_propmpt(base64_image, args)

        # print(response.message.content)
        content = response.message.content
        if not content:
            print("No alt text found for " + id)
            return

        if args.command == "generate-alt-text":
            set_alt_text(elem, content)
            print((f"Alt text set for {id} tag"))
        elif args.command == "generate-table-summary":
            set_table_summary(elem, content)
            print((f"Table summary set for {id} tag"))
        elif args.command == "generate-mathml":
            set_af_math_ml(elem, content)
            print((f"MathML set for {id} tag"))
        else:
            print((f"Unknown operation: {args.subparser}"))

    except Exception as e:
        print("Error: " + str(e))


def browse_tags_recursive(elem: PdsStructElement, args) -> list:
    """
    Recursively browses through the structure elements of a PDF document and processes
    elements that match the specified tags.

    Arguments:
    - parent (PdsStructElement): The parent structure element to start browsing from.
    - doc (PdfDoc): The PDF document containing the structure elements.
    - args (argparse.Namespace): The command-line arguments containing the tags to match.

    Description:
    This function recursively browses through the structure elements of a PDF document
    starting from the specified parent element. It checks each child element to see if it
    matches the specified tags using a regular expression. If a match is found, the element
    is processed using the `process_struct_elem` function. If no match is found, the function
    calls itself recursively on the child element.

    Example:
    # Example usage
    browse_tags_recursive(parent_element, pdf_document, args)
    """
    result = []
    count = elem.GetNumChildren()
    struct_tree = elem.GetStructTree()
    for i in range(0, count):
        if elem.GetChildType(i) != kPdsStructChildElement:
            continue
        child_elem = struct_tree.GetStructElementFromObject(elem.GetChildObject(i))
        if re.match(args.tags, child_elem.GetType(True)) or re.match(args.tags, child_elem.GetType(False)):
            # process element
            result.append(child_elem)
        else:
            result.extend(browse_tags_recursive(child_elem, args))
    return result


def process_pdf(args):
    """
    Processes a PDF document by opening it, checking for a structure tree, and recursively
    browsing through the structure elements to process elements that match the specified tags.

    Arguments:
    - args (argparse.Namespace): The command-line arguments containing the input PDF file,
      output PDF file, license name, license key, and tags to match.

    Description:
    This function initializes the Pdfix library and authorizes it using the provided license
    name and key. It then opens the specified input PDF file and checks if the document has a
    structure tree. If the structure tree is present, it starts browsing through the structure
    elements from the root element and processes elements that match the specified tags using
    the `browse_tags_recursive` function. Finally, it saves the processed PDF to the specified
    output file.

    Example:
    # Example usage
    process_pdf(args)
    """

    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    if args.name and args.key:
        if not pdfix.GetAccountAuthorization().Authorize(args.name, args.key):
            raise Exception(pdfix.GetError())
    elif args.key:
        if not pdfix.GetStandarsAuthorization().Activate(args.key):
            raise Exception(pdfix.GetError())
    else:
        print("No license name or key provided. Using PDFix SDK trial")

    # Open doc
    doc = pdfix.OpenDoc(args.input, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

    struct_tree = doc.GetStructTree()
    if struct_tree is None:
        raise Exception("PDF has no structure tree : " + str(pdfix.GetError()))

    child_elem = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        items = browse_tags_recursive(child_elem, args)
        # for elem in items:
        #     process_struct_elem(elem, args)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_struct_elem, elem, args) for elem in items]
        for future in futures:
            future.result()  # Wait for completion (optional)
    except Exception as e:
        raise e

    if not doc.Save(args.output, kSaveFull):
        raise Exception("Unable to save PDF " + str(pdfix.GetError()))
