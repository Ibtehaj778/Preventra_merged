from pydantic import BaseModel, EmailStr, Field

VALID_ROLES = ["Doctor", "Nurse", "Hospital", "Pharmacy", "Insurance", "Patient"]

ROLE_APP_ACCESS = {
    "Doctor":    ["glp1", "readmissions"],
    "Nurse":     ["glp1", "readmissions"],
    "Hospital":  ["glp1", "readmissions"],
    "Pharmacy":  ["glp1", "readmissions"],
    "Insurance": ["glp1", "readmissions"],
    "Patient":   ["glp1", "readmissions"],
}

class SignupRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=8, max_length=72)
    role:     str
    org_name: str


class UserLogin(BaseModel):
    email:    EmailStr
    password: str = Field(max_length=72)


class UserPublic(BaseModel):
    id:     str
    email:  str
    role:   str
    org_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserPublic