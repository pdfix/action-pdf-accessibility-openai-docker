from pdfixsdk import Pdfix

EC_ARG_GENERAL: int = 10
EC_ARG_NOT_RECOGNIZED_COMMAND: int = 11
EC_ARG_OPENAI_KEY: int = 12
EC_ARG_INPUT_OUTPUT_NOT_ALLOWED: int = 13
EC_ARG_FAILED_TO_READ_IMAGE: int = 14

EC_PDFIX_INITIALIZE: int = 20
EC_PDFIX_ACTIVATION_FAILED: int = 21
EC_PDFIX_AUTHORIZATION_FAILED: int = 22
EC_PDFIX_FAILED_TO_RENDER: int = 23
EC_PDFIX_FAILED_TO_OPEN: int = 24
EC_PDFIX_FAILED_TO_SAVE: int = 25
EC_PDFIX_NO_TAGS: int = 26

EC_OPENAI_GENERAL_ERROR: int = 30
EC_OPENAI_AUTHENTICATION_FAILED: int = 31
EC_OPENAI_RATE_LIMIT_ERROR: int = 32
EC_OPENAI_SERVICE_UNAVAILABLE: int = 33

MESSAGE_ARG_GENERAL: str = "Failed to parse arguments. Please check the usage and try again."
MESSAGE_ARG_NOT_RECOGNIZED_COMMAND: str = "Not recognized command. Please see --help."
MESSAGE_ARG_OPENAI_KEY: str = "Invalid or missing arguments for OpenAI Api Key."
MESSAGE_ARG_INPUT_OUTPUT_NOT_ALLOWED: str = "Not allowed input output file combination. Please see --help."
MESSAGE_ARG_FAILED_TO_READ_IMAGE: str = "Failed to read image data from input."

MESSAGE_PDFIX_INITIALIZE: str = "Failed to initialize PDFix SDK."
MESSAGE_PDFIX_ACTIVATION_FAILED: str = "Failed to activate PDFix SDK account."
MESSAGE_PDFIX_AUTHORIZATION_FAILED: str = "Failed to authorize PDFix SDK account."
MESSAGE_PDFIX_FAILED_TO_RENDER: str = "Failed to render PDF Page into image."
MESSAGE_PDFIX_FAILED_TO_OPEN: str = "Failed to open PDF document."
MESSAGE_PDFIX_FAILED_TO_SAVE: str = "Failed to save PDF document."
MESSAGE_PDFIX_NO_TAGS: str = "PDF document has no tags."

MESSAGE_OPENAI_GENERAL_ERROR: str = "OpenAI service error occurred while processing the request."
MESSAGE_OPENAI_AUTHENTICATION_FAILED: str = "OpenAI Api Key failed to authenticate."
MESSAGE_OPENAI_RATE_LIMIT_ERROR: str = (
    "You exceeded your current quota, please check your OpenAI plan and billing details."
)
MESSAGE_OPENAI_SERVICE_UNAVAILABLE: str = "OpenAI service is temporarily unavailable. Please try again later."


class ExpectedException(BaseException):
    def __init__(self, error_code: int) -> None:
        self.error_code: int = error_code
        self.message: str = ""

    def _add_note(self, note: str) -> None:
        self.message = note


class ArgumentException(ExpectedException):
    def __init__(self, message: str = MESSAGE_ARG_GENERAL, error_code: int = EC_ARG_GENERAL) -> None:
        super().__init__(error_code)
        self._add_note(message)


class ArgumentUnknownCommandException(ArgumentException):
    def __init__(self, command: str) -> None:
        super().__init__(f"{MESSAGE_ARG_NOT_RECOGNIZED_COMMAND} {command}", EC_ARG_NOT_RECOGNIZED_COMMAND)


class ArgumentOpenAIKeyException(ArgumentException):
    def __init__(self) -> None:
        super().__init__(MESSAGE_ARG_OPENAI_KEY, EC_ARG_OPENAI_KEY)


class ArgumentInputOutputNotAllowedException(ArgumentException):
    def __init__(self, message: str = "") -> None:
        super().__init__(f"{MESSAGE_ARG_INPUT_OUTPUT_NOT_ALLOWED} {message}", EC_ARG_INPUT_OUTPUT_NOT_ALLOWED)


class ArgumentFailedToReadImageException(ArgumentException):
    def __init__(self, path: str) -> None:
        super().__init__(f"{MESSAGE_ARG_FAILED_TO_READ_IMAGE} {path}", EC_ARG_FAILED_TO_READ_IMAGE)


class PdfixInitializeException(ExpectedException):
    def __init__(self) -> None:
        super().__init__(EC_PDFIX_INITIALIZE)
        self._add_note(MESSAGE_PDFIX_INITIALIZE)


class PdfixException(ExpectedException):
    def __init__(self, pdfix: Pdfix, error_code: int, message: str = "") -> None:
        super().__init__(error_code)
        pdfix_error_code: int = pdfix.GetErrorType()
        pdfix_error: str = str(pdfix.GetError())
        self._add_note(
            f"[{pdfix_error_code}] [{pdfix_error}]: {message}"
            if len(message) > 0
            else f"[{pdfix_error_code}] {pdfix_error}"
        )


class PdfixActivationException(PdfixException):
    def __init__(self, pdfix: Pdfix) -> None:
        super().__init__(pdfix, EC_PDFIX_ACTIVATION_FAILED, MESSAGE_PDFIX_ACTIVATION_FAILED)


class PdfixAuthorizationException(PdfixException):
    def __init__(self, pdfix: Pdfix) -> None:
        super().__init__(pdfix, EC_PDFIX_AUTHORIZATION_FAILED, MESSAGE_PDFIX_AUTHORIZATION_FAILED)


class PdfixFailedToRenderException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, EC_PDFIX_FAILED_TO_RENDER, f"{MESSAGE_PDFIX_FAILED_TO_RENDER} {message}")


class PdfixFailedToOpenException(PdfixException):
    def __init__(self, pdfix: Pdfix, pdf_path: str = "") -> None:
        super().__init__(pdfix, EC_PDFIX_FAILED_TO_OPEN, f"{MESSAGE_PDFIX_FAILED_TO_OPEN} {pdf_path}")


class PdfixFailedToSaveException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, EC_PDFIX_FAILED_TO_SAVE, f"{MESSAGE_PDFIX_FAILED_TO_SAVE} {message}")


class PdfixNoTagsException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, EC_PDFIX_NO_TAGS, f"{MESSAGE_PDFIX_NO_TAGS} {message}")


class OpenAIException(ExpectedException):
    def __init__(self, error_code: int, message: str) -> None:
        super().__init__(error_code)
        self._add_note(message)


class OpenAIGeneralException(OpenAIException):
    def __init__(self, message: str = "") -> None:
        super().__init__(EC_OPENAI_GENERAL_ERROR, f"{MESSAGE_OPENAI_GENERAL_ERROR} {message}")


class OpenAIAuthenticationException(OpenAIException):
    def __init__(self, message: str = "") -> None:
        super().__init__(EC_OPENAI_AUTHENTICATION_FAILED, f"{MESSAGE_OPENAI_AUTHENTICATION_FAILED} {message}")


class OpenAIRateLimitException(OpenAIException):
    def __init__(self, message: str = "") -> None:
        super().__init__(EC_OPENAI_RATE_LIMIT_ERROR, f"{MESSAGE_OPENAI_RATE_LIMIT_ERROR} {message}")


class OpenAIServiceUnavailableException(OpenAIException):
    def __init__(self, message: str = "") -> None:
        super().__init__(EC_OPENAI_SERVICE_UNAVAILABLE, f"{MESSAGE_OPENAI_SERVICE_UNAVAILABLE} {message}")
