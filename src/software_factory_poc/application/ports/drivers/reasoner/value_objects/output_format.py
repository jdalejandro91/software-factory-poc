try:
    from enum import StrEnum, auto
except ImportError:
    from enum import Enum, auto
    class StrEnum(str, Enum):
        pass


class OutputFormat(StrEnum):
    JSON = auto()      # Para datos estructurados estrictos
    XML = auto()       # Para integraciones legacy o SOAP
    MARKDOWN = auto()  # Para documentación o contenido legible
    TEXT = auto()      # Para chat natural o razonamiento (CoT)
