from typing import Callable, Dict, Any, List, Optional
import functools
from pydantic import BaseModel

class BaseTool(BaseModel):
    name: str
    description: str
    func: Callable
    destructive: bool = False

    class Config:
        arbitrary_types_allowed = True

# Global registry dict mapping tool name to BaseTool instance
tool_registry: Dict[str, BaseTool] = {}

def tool(name: Optional[str] = None, description: Optional[str] = None, destructive: bool = False):
    """
    Decorator to register a function as a KLAUSE tool.
    """
    def decorator(func: Callable):
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Runs the {tool_name} tool."
        
        tool_instance = BaseTool(
            name=tool_name,
            description=tool_desc.strip(),
            func=func,
            destructive=destructive
        )
        
        tool_registry[tool_name] = tool_instance
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_tool_definitions() -> str:
    """
    Format registered tools for the LLM prompt with their exact signatures.
    """
    import inspect
    lines = []
    for name, tool_inst in tool_registry.items():
        sig = inspect.signature(tool_inst.func)
        params_list = []
        for param_name, param in sig.parameters.items():
            if param_name in ("confirm_fn", "self", "args", "kwargs"):
                continue
            
            default_str = ""
            if param.default != inspect.Parameter.empty:
                default_str = f"={repr(param.default)}"
            params_list.append(f"{param_name}{default_str}")
            
        params_str = ", ".join(params_list)
        destructive_str = " (DESTRUCTIVE)" if tool_inst.destructive else ""
        lines.append(f"- {name}({params_str}){destructive_str}: {tool_inst.description}")
    return "\n".join(lines)
