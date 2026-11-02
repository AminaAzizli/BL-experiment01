from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    exploration_level: float
    patience_level: float
    verification_level: float
    retry_limit: int
    instruction_dependence: float
    decision_style: str
    strategy_guidance: str


PERSONAS: dict[str, Persona] = {
    "neutral_baseline": Persona(
        name="neutral_baseline",
        exploration_level=0.5,
        patience_level=0.5,
        verification_level=0.5,
        retry_limit=3,
        instruction_dependence=0.5,
        decision_style="balanced",
        strategy_guidance="Explore in a balanced way, make decisions at a normal pace, and verify the outcome moderately.",
    ),
    "low_digital_experience": Persona(
        name="low_digital_experience",
        exploration_level=0.55,
        patience_level=0.65,
        verification_level=0.7,
        retry_limit=4,
        instruction_dependence=0.9,
        decision_style="stepwise",
        strategy_guidance="Rely on visible instructions, take one action at a time, and inspect the page after important actions.",
    ),
    "low_patience": Persona(
        name="low_patience",
        exploration_level=0.2,
        patience_level=0.2,
        verification_level=0.35,
        retry_limit=1,
        instruction_dependence=0.4,
        decision_style="direct",
        strategy_guidance="Prefer a direct path, avoid repeated unsuccessful actions, and do only enough exploration to proceed.",
    ),
    "low_risk_tolerance": Persona(
        name="low_risk_tolerance",
        exploration_level=0.45,
        patience_level=0.75,
        verification_level=0.95,
        retry_limit=4,
        instruction_dependence=0.7,
        decision_style="cautious",
        strategy_guidance="Verify selections before important actions, avoid guessing when unclear, and prefer clear confirmation.",
    ),
    "high_experience": Persona(
        name="high_experience",
        exploration_level=0.35,
        patience_level=0.8,
        verification_level=0.85,
        retry_limit=3,
        instruction_dependence=0.25,
        decision_style="efficient",
        strategy_guidance="Use familiar interface conventions efficiently, explore confidently, and verify the final result without needless repetition.",
    ),
}


def get_persona(name: str) -> Persona:
    try:
        return PERSONAS[name]
    except KeyError as error:
        supported = ", ".join(sorted(PERSONAS))
        raise ValueError(f"Unknown persona '{name}'. Choose one of: {supported}") from error


def persona_parameters(name: str) -> dict[str, object]:
    return asdict(get_persona(name))
