import base64
import ctypes
import re
from ai import openai_propmpt

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


def process_struct_elem(elem: PdsStructElement, doc: PdfDoc, args):
    try:
        elem_obj_id = elem.GetObject().GetId()
        elem_id = elem.GetId()
        elem_type = elem.GetType(False)
        elem_type_mapped = elem.GetType(True)

        page_num = elem.GetPageNumber(0)
        if page_num == -1:
            for i in range(0, elem.GetNumChildren()):
                page_num = elem.GetChildPageNumber(i)
                if page_num != -1:
                    break

        id = f"{elem_type} [obj: {elem_obj_id}]"

        # get the object page number (it may be written in child objects)
        if page_num == -1:
            print(
                "Skipping ["
                + id
                + "] tag that matches the search criteria but can't determine the page number"
            )
            return

        id += ", page: " + str(page_num + 1)

        # get image bbox
        bbox = PdfRect()
        for i in range(elem.GetNumPages()):
            page_num = elem.GetPageNumber(i)
            bbox = elem.GetBBox(page_num)
            break

        # check bounding box
        if bbox.left == bbox.right or bbox.top == bbox.bottom:
            print(
                "Skipping ["
                + id
                + "] tag that matches the search criteria but can't determine the bounding box"
            )
            return

        print((f"Processing {id} tag matches the search criteria ..."))

        org_alt = elem.GetAlt()
        if not args.overwrite and org_alt:
            print((f"Alt text already exists for {id} tag"))
            return

        data = render_page(doc, page_num, bbox, 1)
        base64_image = base64.b64encode(data).decode("utf-8")
        # with open(img, "wb") as bf:
        #     bf.write(data)

        print((f"Talking to OpenAI for {id} tag ..."))
        response = openai_propmpt(base64_image, args)

        # print(response.message.content)
        content = response.message.content
        if not content:
            print("No alt text found for " + id)
            return

        if args.subparser == "generate-alt-text":
            elem.SetAlt(content)
            print((f"Alt text set for {id} tag"))
        elif args.subparser == "generate-table-summary":
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

            attr_dict.PutString("Summary", content)
            print((f"Table summary set for {id} tag"))
        else:
            print((f"Unknown operation: {args.subparser}"))

    except Exception as e:
        print("Error: " + str(e))


def set_table_summary(
    elem: PdsStructElement,
    doc: PdfDoc,
) -> None:
    img = "table_" + str(elem.GetObject().GetId()) + ".jpg"
    print("[" + img + "] table found with an id " + img)

    # get the object page number (it may be written in child objects)
    pages = elem.GetNumPages()
    if pages == 0:
        print("[" + img + "] table found but can't determine the page number")
        return

    page_num = elem.GetPageNumber(0)
    if page_num == -1:
        print("[" + img + "] unable to retrieve the page number from tag")
        return

    bbox = elem.GetBBox(page_num)
    # check bounding box
    if bbox.left == bbox.right or bbox.top == bbox.bottom:
        print("[" + img + "] table found but no BBox attribute was set")
        return

    data = render_page(doc, page_num, bbox, 1)
    with open(img, "wb") as bf:
        bf.write(data)

    response = table_summary(img, api_key, lang)

    # print(response.message.content)
    summary = response.message.content

    if not summary or summary == "":
        print("[" + img + "] no summary generated")
        return

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

    old_summary = attr_dict.GetText("Summary")
    if overwrite or not old_summary:
        print("[" + img + "] summary attribute updated")
        attr_dict.PutString("Summary", summary)


def browse_tags_recursive(parent: PdsStructElement, doc: PdfDoc, args):
    count = parent.GetNumChildren()
    struct_tree = doc.GetStructTree()
    for i in range(0, count):
        if parent.GetChildType(i) != kPdsStructChildElement:
            continue
        child_elem = struct_tree.GetStructElementFromObject(parent.GetChildObject(i))
        if re.match(args.tags, child_elem.GetType(True)):
            # process element

            # process figure element
            process_struct_elem(child_elem, doc, args)
        else:
            browse_tags_recursive(child_elem, doc, args)


def process_pdf(args):
    #     input_path: str,
    #     output_path: str,
    #     tags: str,
    #     license_name: str,
    #     license_key: str,
    #     api_key: str,
    #     overwrite: bool,
    #     lang: str,
    # ) -> None:
    """Run OpenAI for alternate text description.

    Parameters
    ----------
    input_path : str
        Input path to the PDF file.
    output_path : str
        Output path for saving the PDF file.
    license_name : str
        Pdfix SDK license name.
    license_key : str
        Pdfix SDK license key.
    api_key : str
        OpenAI API key.
    overwrite : bool
        Ovewrite alternate text if already present.
    lang : str
        Alternate description language.

    """
    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    if args.name and args.key:
        if not pdfix.GetAccountAuthorization().Authorize(args.name, args.key):
            raise Exception("Pdfix Authorization fail")
    else:
        print("No license name or key provided. Using Pdfix trial")

    # Open doc
    doc = pdfix.OpenDoc(args.input, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

    struct_tree = doc.GetStructTree()
    if struct_tree is None:
        raise Exception("PDF has no structure tree : " + str(pdfix.GetError()))

    child_elem = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        browse_tags_recursive(child_elem, doc, args)
    except Exception as e:
        raise e

    if not doc.Save(args.output, kSaveFull):
        raise Exception("Unable to save PDF " + str(pdfix.GetError()))
