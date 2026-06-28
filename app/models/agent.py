from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentAction(BaseModel):
    thought: str = Field(..., description="Your step-by-step reasoning on what to do next.")
    action: str = Field(..., description="The name of the tool to invoke, or 'FINAL' when done.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Key-value parameters to pass to the tool.")
    response: Optional[str] = Field(None, description="The final answer to the user (only set when action='FINAL').")

class ToolObservation(BaseModel):
    tool_name: str
    success: bool
    result: str
    error: Optional[str] = None
