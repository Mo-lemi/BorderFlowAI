from pydantic import BaseModel, Field
from typing import Literal


class ForensicAudit(BaseModel):
    extracted_data: dict[str, str] = Field(
        description="Every field legible on the document image, as key/value pairs"
    )
    discrepancies: list[str] = Field(
        description="Each specific mismatch between the declaration and the document. Empty list if none."
    )
    forensic_observations: str = Field(
        description="Document integrity assessment: tampering indicators, metadata analysis"
    )
    physical_logic_assessment: str = Field(
        description="Whether the declared weight is physically plausible for the declared commodity"
    )
    regulatory_compliance: str = Field(
        description="Whether the permit class matches the cargo type"
    )
    confidence_score: int = Field(ge=1, le=10)
    recommended_action: Literal[
        "PROCEED_TO_LANE", "SECONDARY_INSPECTION", "DETAIN_FOR_INVESTIGATION"
    ]
