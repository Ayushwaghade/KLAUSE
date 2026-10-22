import inspect
from typing import Callable, Dict, Any, Optional
from loguru import logger
from app.tools.base import tool_registry
from app.models.agent import ToolObservation

class Dispatcher:
    def __init__(self, confirm_fn: Optional[Callable[[str], bool]] = None):
        self.confirm_fn = confirm_fn or self._default_console_confirm

    def _default_console_confirm(self, prompt: str) -> bool:
        """Default confirmation routine for CLI or Web UI routing."""
        logger.info(f"Requesting confirmation: {prompt}")
        from app.core.context import context
        
        session_id = context.session_id
        if session_id in context._active_connections:
            return context.request_confirmation(session_id, prompt)
            
        try:
            print(f"\n[CONFIRMATION REQUIRED]: {prompt}")
            response = input("Approve? (y/N): ").strip().lower()
            approved = response in ("y", "yes")
            logger.info(f"Confirmation response: {approved}")
            return approved
        except Exception as e:
            logger.error(f"Exception during confirmation check: {e}")
            return False

    def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolObservation:
        logger.info(f"Executing tool: {tool_name} with params: {params}")
        
        if tool_name not in tool_registry:
            error_msg = f"Tool '{tool_name}' not found in registry."
            logger.error(error_msg)
            return ToolObservation(
                tool_name=tool_name,
                success=False,
                result="",
                error=error_msg
            )
            
        tool_inst = tool_registry[tool_name]
        
        try:
            # Code-level boundary check for Universal Rule 1 (Session Data Folder)
            from app.core.context import context
            session_folder = context.session_data_folder
            if session_folder:
                import os
                target_path = None
                if "path" in params:
                    target_path = params["path"]
                elif "output_path" in params:
                    target_path = params["output_path"]
                elif "dest" in params:
                    target_path = params["dest"]
                elif "dest_path" in params:
                    target_path = params["dest_path"]

                write_tools = ["write_file", "download_file", "fs_copy", "fs_move", "fs_delete", "download_image"]
                if tool_name in write_tools and target_path:
                    abs_target = os.path.abspath(target_path)
                    abs_session = os.path.abspath(session_folder)
                    if not abs_target.startswith(abs_session):
                        prompt_text = (
                            f"Rule Violation Warning: Tool '{tool_name}' wants to write outside the active session "
                            f"folder to '{abs_target}'. Allow this write exception?"
                        )
                        approved = self.confirm_fn(prompt_text)
                        if not approved:
                            return ToolObservation(
                                tool_name=tool_name,
                                success=False,
                                result="",
                                error=f"RULE_VIOLATION: Writing to '{abs_target}' blocked by user."
                            )

            # Map parameters and filter out unused/hallucinated keyword arguments
            sig = inspect.signature(tool_inst.func)
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            
            kwargs = {}
            for name, val in params.items():
                if name in sig.parameters or has_var_keyword:
                    kwargs[name] = val
                else:
                    logger.warning(f"Ignored unrecognized parameter '{name}' passed to tool '{tool_name}'.")
            
            # Inject confirmation callback if accepted by the tool signature
            if "confirm_fn" in sig.parameters:
                kwargs["confirm_fn"] = self.confirm_fn
                
            # If tool is marked as destructive at decorator level, double check confirmation
            if tool_inst.destructive:
                if tool_name == "run_terminal_command":
                    prompt_text = f"Execute terminal command: '{params.get('command')}'"
                elif tool_name == "run_terminal_command_async":
                    prompt_text = f"Execute background terminal command: '{params.get('command')}'"
                elif tool_name == "desktop_macro":
                    steps = params.get("steps", [])
                    if isinstance(steps, str):
                        try:
                            import json
                            steps = json.loads(steps)
                        except Exception:
                            pass
                    if isinstance(steps, list):
                        summary_items = []
                        for s in steps[:5]:
                            if isinstance(s, dict):
                                act = s.get("action", "")
                                if act == "hotkey":
                                    summary_items.append(f"hotkey({s.get('keys')})")
                                elif act == "type":
                                    preview = str(s.get('text', ''))[:15]
                                    summary_items.append(f"type('{preview}')")
                                elif act == "click":
                                    summary_items.append(f"click({s.get('x')}, {s.get('y')})")
                                elif act == "keypress":
                                    summary_items.append(f"press({s.get('key')})")
                                elif act in ("wait", "sleep"):
                                    summary_items.append(f"wait({s.get('seconds', 0.5)}s)")
                                else:
                                    summary_items.append(act)
                            else:
                                summary_items.append(str(s))
                        if len(steps) > 5:
                            summary_items.append(f"+{len(steps)-5} more")
                        prompt_text = f"Execute desktop macro ({len(steps)} steps): " + " -> ".join(summary_items)
                    else:
                        prompt_text = f"Execute desktop macro: {str(steps)[:100]}"
                else:
                    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                    prompt_text = f"Run destructive tool '{tool_name}' with parameters: ({param_str})"
                
                approved = self.confirm_fn(prompt_text)
                if not approved:
                    return ToolObservation(
                        tool_name=tool_name,
                        success=False,
                        result="",
                        error=f"Execution of destructive tool '{tool_name}' rejected by user."
                    )
            
            # Execute actual function
            result = tool_inst.func(**kwargs)
            res_str = str(result).strip()
            
            # Detect string-level error responses returned without exceptions
            is_err_str = res_str.lower().startswith(("error:", "error ", "failed:", "failure:"))
            if is_err_str:
                logger.warning(f"Tool '{tool_name}' returned error output: {res_str[:120]}")
                context.last_error = res_str[:200]
                return ToolObservation(
                    tool_name=tool_name,
                    success=False,
                    result="",
                    error=res_str
                )

            logger.info(f"Tool '{tool_name}' execution succeeded.")
            context.last_tool_used = tool_name
            
            return ToolObservation(
                tool_name=tool_name,
                success=True,
                result=res_str,
                error=None
            )
            
        except TypeError as te:
            error_msg = f"Invalid parameters passed to tool '{tool_name}': {te}"
            logger.error(error_msg)
            context.last_error = str(te)[:200]
            return ToolObservation(
                tool_name=tool_name,
                success=False,
                result="",
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Execution error in tool '{tool_name}': {e}"
            logger.exception(error_msg)
            context.last_error = str(e)[:200]
            return ToolObservation(
                tool_name=tool_name,
                success=False,
                result="",
                error=error_msg
            )
