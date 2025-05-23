import ctypes

from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    PdfImageParams,
    PdfPageRenderParams,
    PdfRect,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kRotate0,
)


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
