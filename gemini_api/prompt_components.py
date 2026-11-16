"""Composite imutável: trechos e grupos de prompt têm o mesmo contrato."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ComponentePrompt(ABC):
    @abstractmethod
    def renderizar(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class TrechoPrompt(ComponentePrompt):
    texto: str

    def renderizar(self) -> str:
        return self.texto


@dataclass(frozen=True)
class GrupoPrompt(ComponentePrompt):
    componentes: tuple[ComponentePrompt, ...]

    def __post_init__(self):
        # Uma lista recebida do chamador não deve modificar a árvore depois.
        object.__setattr__(self, 'componentes', tuple(self.componentes))

    def renderizar(self) -> str:
        return '\n'.join(componente.renderizar() for componente in self.componentes)
