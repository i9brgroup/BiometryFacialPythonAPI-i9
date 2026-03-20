from pydantic import BaseModel


class EmployeePayload(BaseModel):
    id: str
    name: str
    email: str
    siteId: str
    localId: str
    photoKey: str

class ApiPayload(BaseModel):
    siteId: str
    localId: str