import ctypes
import io
from typing import Optional

from pdfixsdk import (
    PdfDevRect,
    PdfDoc,
    PdfImageParams,
    Pdfix,
    PdfPage,
    PdfPageRenderParams,
    PdfPageView,
    PdfRect,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kRotate0,
)
from PIL import Image

from exceptions import PdfixException


def render_page(pdfix: Pdfix, doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    """
    Render PDF document page to bytearray image.

    Args:
        pdfix (Pdfix): Pdfix SDK.
        doc (PdfDoc): The PDF document to render.
        page_num (int): The page number to render.
        bbox (PdfRect): The bounding box of the page to render.
        zoom (float): The zoom level for rendering.

    Returns:
        The rendered image data as a bytearray.
    """
    page: PdfPage = doc.AcquirePage(page_num)
    if page is None:
        raise PdfixException(pdfix, "Unable to acquire the page")

    try:
        page_view: PdfPageView = page.AcquirePageView(zoom, kRotate0)
        if page_view is None:
            raise PdfixException(pdfix, "Unable to acquire page view")

        try:
            rect: PdfDevRect = page_view.RectToDevice(bbox)

            # render content
            render_parameters = PdfPageRenderParams()
            render_parameters.matrix = page_view.GetDeviceMatrix()
            render_parameters.clip_box = bbox
            render_parameters.image = pdfix.CreateImage(
                rect.right - rect.left,
                rect.bottom - rect.top,
                kImageDIBFormatArgb,
            )
            if render_parameters.image is None:
                raise PdfixException(pdfix, "Unable to create the image")

            try:
                if not page.DrawContent(render_parameters):
                    raise PdfixException(pdfix, "Unable to draw the content")

                # save image to stream and data
                memory_stream = pdfix.CreateMemStream()
                if memory_stream is None:
                    raise PdfixException(pdfix, "Unable to create memory stream")

                try:
                    image_parameters = PdfImageParams()
                    image_parameters.format = kImageFormatJpg

                    if not render_parameters.image.SaveToStream(memory_stream, image_parameters):
                        raise PdfixException(pdfix, "Unable to save the image to the stream")

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


def get_image_bytes(image_path: str) -> Optional[bytes]:
    try:
        with Image.open(image_path) as image:
            buffered = io.BytesIO()
            image.save(buffered, format="jpg")
            return buffered.getvalue()
    except Exception:
        raise

    return None
