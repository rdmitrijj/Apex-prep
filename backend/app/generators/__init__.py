"""Math question generators (pure Python + SymPy). `generate(subskill_id, difficulty, rng)`."""

import random

from app.generators import adv, alg, geo, psd  # noqa: F401  (registers generators)
from app.generators.core import DIFFICULTIES, REGISTRY, Difficulty, Generated

__all__ = ["DIFFICULTIES", "REGISTRY", "Difficulty", "Generated", "generate"]


def generate(subskill_id: str, difficulty: Difficulty, rng: random.Random) -> Generated:
    return REGISTRY[subskill_id](rng, difficulty)
