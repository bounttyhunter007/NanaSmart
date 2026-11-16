from abc import ABC, abstractmethod
from .prompt import Prompt

class PromptBuilder(ABC):
    @abstractmethod
    def com_contexto(self, context_str: str) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_alertas(self, alertas: list) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_ordens(self, ordens: list, titulo: str) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_telemetria(self, dados: list) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_financeiro(self, dados: list) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_instrucoes(self, texto: str) -> 'PromptBuilder':
        pass

    @abstractmethod
    def com_pergunta(self, texto: str) -> 'PromptBuilder':
        pass

    @abstractmethod
    def build(self) -> Prompt:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class PromptBuilderConcreto(PromptBuilder):
    def __init__(self):
        self._blocos = []
        self._max_linhas = 5

    def reset(self):
        self._blocos = []

    def _truncar(self, linhas: list, max_linhas: int) -> list:
        if len(linhas) <= max_linhas:
            return linhas
        return linhas[:max_linhas] + [f"... ({len(linhas) - max_linhas} itens adicionais omitidos)"]

    def com_contexto(self, context_str: str) -> 'PromptBuilder':
        if context_str:
            self._blocos.append(context_str)
        return self

    def com_alertas(self, alertas: list) -> 'PromptBuilder':
        if alertas:
            linhas = [f"- {linha}" if not linha.startswith("-") else linha for linha in alertas]
            truncadas = self._truncar(linhas, self._max_linhas)
            if truncadas:
                self._blocos.append("\nALERTAS RELEVANTES:\n" + "\n".join(truncadas))
        return self

    def com_ordens(self, ordens: list, titulo: str) -> 'PromptBuilder':
        if ordens:
            linhas = [f"- {linha}" if not linha.startswith("-") else linha for linha in ordens]
            truncadas = self._truncar(linhas, self._max_linhas)
            if truncadas:
                self._blocos.append(f"\n{titulo}:\n" + "\n".join(truncadas))
        return self

    def com_telemetria(self, dados: list) -> 'PromptBuilder':
        if dados:
            truncadas = self._truncar(dados, self._max_linhas)
            if truncadas:
                self._blocos.append("\nTELEMETRIA RECENTE:\n" + "\n".join(truncadas))
        return self

    def com_financeiro(self, blocos_financeiros: list) -> 'PromptBuilder':
        if blocos_financeiros:
            self._blocos.append("\n".join(blocos_financeiros))
        return self

    def com_instrucoes(self, texto: str) -> 'PromptBuilder':
        if texto:
            self._blocos.append(f"\n{texto}")
        return self

    def com_pergunta(self, texto: str) -> 'PromptBuilder':
        if texto:
            self._blocos.append(f"\nPERGUNTA DO USUÁRIO:\n{texto}")
        return self

    def build(self) -> Prompt:
        resultado = "\n".join(self._blocos)
        return Prompt(resultado)
