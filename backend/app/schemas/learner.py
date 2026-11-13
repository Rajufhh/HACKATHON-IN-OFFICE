from pydantic import BaseModel, ConfigDict, EmailStr

class LearnerCreate(BaseModel):
    learner_code: str
    name: str
    email: EmailStr
    department: str

class LearnerResponse(BaseModel):
    id: int
    learner_code: str
    name: str
    email: EmailStr
    department: str
    status: str

    model_config = ConfigDict(from_attributes=True)

