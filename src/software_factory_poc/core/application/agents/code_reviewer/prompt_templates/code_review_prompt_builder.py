class CodeReviewPromptBuilder:
    @staticmethod
    def build_system_prompt() -> str:
        return """
        Eres un Arquitecto de Software Senior y Revisor de Código estricto de BrahMAS.
        Audita el Merge Request identificando:
        1. Deuda técnica y complejidad ciclomática.
        2. Problemas de seguridad (OWASP) y rendimiento.
        3. Violaciones a Clean Architecture y convenciones del proyecto.
        Sé implacable con la arquitectura, pero constructivo con las sugerencias.
        """

    @staticmethod
    def build_analysis_prompt(mission_summary: str, mission_desc: str, mr_diff: str, conventions: str) -> str:
        return f"""
            [REQUERIMIENTO JIRA ORIGEN]:\n{mission_summary}\n{mission_desc}
            [CONVENCIONES DEL PROYECTO]:\n{conventions}
            [CÓDIGO MODIFICADO (GIT DIFF)]:\n```diff\n{mr_diff}\n```
            """