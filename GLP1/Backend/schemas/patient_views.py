"""
Role-narrowed response shapes (Task C, Section 6 pattern).
"""

from pydantic import BaseModel
from typing import Optional


class PatientPharmacyView(BaseModel):
    patient_idx:         int
    assigned_molecule:   str
    drug_generation:     Optional[int] = None
    system_refill_score: Optional[float] = None