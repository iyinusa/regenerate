from typing import Optional, Dict
from pydantic import BaseModel, Field

class PrivacyBase(BaseModel):
    is_public: bool = Field(default=False, description="Whether the profile is publicly accessible")
    hidden_sections: Dict[str, bool] = Field(default_factory=dict, description="Dictionary where key is section name and value is boolean (True=Hidden)")

class PrivacyUpdate(PrivacyBase):
    username: Optional[str] = Field(None, description="Public username for the profile URL")

class PrivacyResponse(PrivacyBase):
    user_id: str
    username: Optional[str] = None
    
    class Config:
        from_attributes = True
