"""Experimental cells only; production model and recall defaults are untouched."""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0864
REVISION = "858a1ac046a05663a35367eac852d7f76feeefdd"
REPOSITORY = "prithivida/flashrank"
# source: ADR-0864
FLASHRANK_VERSION = "0.2.10"
# source: ADR-0864
MULTIPLIERS = (2, 3)


@dataclass(frozen=True)
class ModelPin:
    name: str
    filename: str
    archive_sha256: str

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{self.name}.zip"


# source: ADR-0864
MODELS = {
    "l2": ModelPin(
        "ms-marco-TinyBERT-L-2-v2",
        "flashrank-TinyBERT-L-2-v2.onnx",
        "752eddf1c5ece3c5e6115e9ab52eb3b16436bbf9b3a091cbb62b5b8eadc47105",
    ),
    "l12": ModelPin(
        "ms-marco-MiniLM-L-12-v2",
        "flashrank-MiniLM-L-12-v2_Q.onnx",
        "bdd3772b651ffc34f70e414049285bb55ccc6d1b8e29d0640f836d44f70ec77a",
    ),
}


@dataclass(frozen=True)
class Cell:
    model: ModelPin
    multiplier: int
    name: str


def cell(name: str) -> Cell:
    for model, pin in MODELS.items():
        for multiplier in MULTIPLIERS:
            if name == f"{model}-{multiplier}x":
                return Cell(pin, multiplier, name)
    raise ValueError(f"unknown W4-2 cell: {name}")
