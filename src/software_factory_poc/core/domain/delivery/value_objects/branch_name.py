from dataclasses import dataclass


@dataclass(frozen=True)
class BranchName:
    value: str

    def __post_init__(self):
        val = self.value.strip()
        if not val or " " in val:
            raise ValueError("El nombre de la rama no puede estar vacío ni contener espacios.")
        if not val.startswith(("feature/", "hotfix/", "release/", "poc/")):
            raise ValueError(f"Alucinación de IA: Convención de rama inválida '{val}'")
