from enum import Enum
class Decision(str, Enum):
    PROCEED = "PROCEED"
    CONFIRM = "CONFIRM"
    ESCALATE = "ESCALATE"
class Urgency(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
DECISION_COLORS = {
    Decision.PROCEED: "green",
    Decision.CONFIRM: "yellow",
    Decision.ESCALATE: "red",
}
def decide_action(urgency: Urgency, confidence: float) -> Decision:
    if urgency == Urgency.HIGH:
        return Decision.ESCALATE
    if confidence < 0.65:
        return Decision.CONFIRM
    return Decision.PROCEED
def get_decision_color(decision: Decision) -> str:
    return DECISION_COLORS[decision]
