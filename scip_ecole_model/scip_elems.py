from dataclasses import dataclass


@dataclass(frozen=True)
class SCIPAttributes:
    """
    Класс атрибутов решателя SCIP
    """

    LIMITS_TIME = "limits/time"

    STATUS_TIMELIMIT = "timelimit"
    STATUS_USERINTERRUPT = "userinterrupt"
    STATUS_GAPLIMIT = "gaplimit"
