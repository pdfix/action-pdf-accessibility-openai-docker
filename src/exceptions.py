from pdfixsdk import Pdfix

EC_ARG_GENERAL = 10
EC_ARG_NOT_RECOGNIZED_COMMAND = 11
EC_ARG_OPENAI_KEY = 12
EC_ARG_INPUT_OUTPUT_NOT_ALLOWED = 13
EC_ARG_FAILED_TO_READ_IMAGE = 14

EC_PDFIX_INITIALIZE = 20
EC_PDFIX_ACTIVATION_FAILED = 21
EC_PDFIX_AUTHORIZATION_FAILED = 22
EC_PDFIX_FAILED_TO_RENDER = 23
EC_PDFIX_FAILED_TO_OPEN = 24
EC_PDFIX_FAILED_TO_SAVE = 25
EC_PDFIX_NO_TAGS = 26

EC_OPENAI_AUTHENTICATION_FAILED = 30

MESSAGE_ARG_GENERAL = "Failed to parse arguments. Please check the usage and try again."
MESSAGE_ARG_NOT_RECOGNIZED_COMMAND = "Not recognized command. Please see --help."
MESSAGE_ARG_OPENAI_KEY = "Invalid or missing arguments for OpenAI Api Key."
MESSAGE_ARG_INPUT_OUTPUT_NOT_ALLOWED = "Not allowed input output file combination. Please see --help."
MESSAGE_ARG_FAILED_TO_READ_IMAGE = "Failed to read image data from input."

MESSAGE_PDFIX_INITIALIZE = "Failed to initialize PDFix SDK."
MESSAGE_PDFIX_ACTIVATION_FAILED = "Failed to activate PDFix SDK acount."
MESSAGE_PDFIX_AUTHORIZATION_FAILED = "Failed to authorize PDFix SDK acount."
MESSAGE_PDFIX_FAILED_TO_RENDER = "Failed to render PDF Page into image."
MESSAGE_PDFIX_FAILED_TO_OPEN = "Failed to open PDF document."
MESSAGE_PDFIX_FAILED_TO_SAVE = "Failed to save PDF document."
MESSAGE_PDFIX_NO_TAGS = "PDF document has no tags."

MESSAGE_OPENAI_AUTHENTICATION_FAILED = "OpenAI Api Key failed to authenticate."


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


class PdfixException(Exception):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        error_code = pdfix.GetErrorType()
        error = str(pdfix.GetError())
        self.errno = error_code
        self.add_note(f"[{error_code}] [{error}]: {message}" if len(message) > 0 else f"[{error_code}] {error}")


class PdfixActivationException(PdfixException):
    def __init__(self, pdfix: Pdfix) -> None:
        super().__init__(pdfix, MESSAGE_PDFIX_ACTIVATION_FAILED)
        self.error_code = EC_PDFIX_ACTIVATION_FAILED


class PdfixAuthorizationException(PdfixException):
    def __init__(self, pdfix: Pdfix) -> None:
        super().__init__(pdfix, MESSAGE_PDFIX_AUTHORIZATION_FAILED)
        self.error_code = EC_PDFIX_AUTHORIZATION_FAILED


class PdfixFailedToRenderException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, f"{MESSAGE_PDFIX_FAILED_TO_RENDER} {message}")
        self.error_code = EC_PDFIX_FAILED_TO_RENDER


class PdfixFailedToOpenException(PdfixException):
    def __init__(self, pdfix: Pdfix, pdf_path: str = "") -> None:
        super().__init__(pdfix, f"{MESSAGE_PDFIX_FAILED_TO_OPEN} {pdf_path}")
        self.error_code = EC_PDFIX_FAILED_TO_OPEN


class PdfixFailedToSaveException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, f"{MESSAGE_PDFIX_FAILED_TO_SAVE} {message}")
        self.error_code = EC_PDFIX_FAILED_TO_SAVE


class PdfixNoTagsException(PdfixException):
    def __init__(self, pdfix: Pdfix, message: str = "") -> None:
        super().__init__(pdfix, f"{MESSAGE_PDFIX_NO_TAGS} {message}")
        self.error_code = EC_PDFIX_NO_TAGS


class OpenAIAuthenticationException(ExpectedException):
    def __init__(self, message: str = "") -> None:
        super().__init__(EC_OPENAI_AUTHENTICATION_FAILED)
        self.add_note(f"{MESSAGE_OPENAI_AUTHENTICATION_FAILED} {message}")
