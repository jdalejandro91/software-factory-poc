from dataclasses import dataclass

@dataclass(frozen=True)
class FileContent:
    path: str
    content: str
    is_new: bool = True

    def __post_init__(self):
        if not self.path.strip() or self.path.startswith("/") or ".." in self.path:
            raise ValueError(f"Alucinación de IA: Ruta de archivo inválida o insegura '{self.path}'")