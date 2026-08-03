import os
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger

from app.automation.event_engine import Event, EventType, event_engine
from app.config.config import settings

class RuleModel(BaseModel):
    rule_id: str
    event_type: str
    filter_pattern: Optional[str] = None
    action_type: str  # "tool_call" or "trigger_react"
    action_payload: Dict[str, Any]  # for tool_call: {"tool_name": str, "params": dict}. for trigger_react: {"prompt": str}
    enabled: bool = True


class RuleEngine:
    """
    Manages loading, saving, validating, and executing event-driven automation rules.
    """
    def __init__(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.rules_path = os.path.join(project_root, "data", "rules.json")
        self.rules: List[RuleModel] = []
        self._react_queue: List[str] = []
        self._lock = False
        
        # Load rules on instantiation
        self.load_rules()
        
        # Register rule matcher to event engine
        for et in EventType:
            event_engine.subscribe(et, self.handle_event)

    def load_rules(self):
        """Loads and validates rules from rules.json."""
        if not os.path.exists(self.rules_path):
            os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            self.rules = []
            return

        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read rules file: {e}. Starting with empty rules.")
            self.rules = []
            return

        validated_rules = []
        max_rules = getattr(settings.automation, "max_rules", 50)
        
        for idx, item in enumerate(raw_data):
            if idx >= max_rules:
                logger.warning(f"Soft limit of {max_rules} rules reached. Skipping remaining rules.")
                break
            try:
                rule = RuleModel.model_validate(item)
                validated_rules.append(rule)
            except Exception as ve:
                logger.warning(f"Skipping malformed rule entry at index {idx}: {ve}. Raw: {item}")

        self.rules = validated_rules
        logger.info(f"Successfully loaded and validated {len(self.rules)} rules.")

    def save_rules(self) -> bool:
        """Persists rules to rules.json."""
        try:
            os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
            data = [rule.model_dump() for rule in self.rules]
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Rules saved to rules.json.")
            return True
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            return False

    def add_rule(self, rule: RuleModel) -> str:
        """Adds a validated rule and persists it."""
        max_rules = getattr(settings.automation, "max_rules", 50)
        if len(self.rules) >= max_rules:
            return f"Error: Cannot add rule. Soft limit of {max_rules} rules reached."

        # Verify uniqueness of ID
        for r in self.rules:
            if r.rule_id == rule.rule_id:
                return f"Error: A rule with ID '{rule.rule_id}' already exists."

        # Add and save
        self.rules.append(rule)
        self.save_rules()
        return f"Successfully added rule '{rule.rule_id}'."

    def remove_rule(self, rule_id: str) -> bool:
        """Removes a rule by ID and persists changes."""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        if len(self.rules) < initial_count:
            self.save_rules()
            return True
        return False

    def handle_event(self, event: Event):
        """Processes event, matches rules, and triggers execution."""
        matching_rules = self.match_event(event)
        if not matching_rules:
            return

        logger.info(f"Event {event.event_type.value} matched {len(matching_rules)} rules. Triggering actions.")
        for rule in matching_rules:
            try:
                self.execute_action(rule, event)
            except Exception as e:
                logger.error(f"Error executing action for rule '{rule.rule_id}': {e}")

    def match_event(self, event: Event) -> List[RuleModel]:
        """Matches event against registered rules (first-to-last match sequence)."""
        matches = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.event_type.lower() != event.event_type.value.lower():
                continue

            # If filter pattern is defined, apply regex check on data fields
            if rule.filter_pattern:
                text_to_match = ""
                if event.event_type == EventType.WINDOW_FOCUSED:
                    text_to_match = event.data.get("title", "")
                elif event.event_type == EventType.PROCESS_TERMINATED:
                    text_to_match = event.data.get("command", "")
                elif event.event_type == EventType.FILE_CHANGED:
                    text_to_match = event.data.get("path", "")
                elif event.event_type == EventType.CRON_TRIGGERED:
                    text_to_match = event.data.get("job_id", "")

                try:
                    if not re.search(rule.filter_pattern, text_to_match, re.IGNORECASE):
                        continue
                except Exception as re_err:
                    logger.warning(f"Invalid regex filter pattern in rule '{rule.rule_id}': {re_err}")
                    continue

            matches.append(rule)
        return matches

    def execute_action(self, rule: RuleModel, event: Event):
        """Executes rules through the dispatcher or queues proactive thoughts."""
        logger.info(f"Executing rule action '{rule.rule_id}' (Type: {rule.action_type})")
        
        if rule.action_type == "tool_call":
            tool_name = rule.action_payload.get("tool_name")
            params = rule.action_payload.get("params", {})
            if not tool_name:
                logger.error(f"Rule '{rule.rule_id}' missing 'tool_name' in payload.")
                return

            # Execute via dispatcher to inherit all confirmation gates
            from app.core.dispatcher import Dispatcher
            dispatcher = Dispatcher()
            observation = dispatcher.execute(tool_name, params)
            logger.info(f"Rule '{rule.rule_id}' tool call '{tool_name}' result success: {observation.success}")

        elif rule.action_type == "trigger_react":
            prompt = rule.action_payload.get("prompt")
            if not prompt:
                logger.error(f"Rule '{rule.rule_id}' missing 'prompt' in payload.")
                return

            # Interpolate event variables into prompt if present
            if "{event_source}" in prompt:
                prompt = prompt.replace("{event_source}", event.source)
            if "{event_data}" in prompt:
                prompt = prompt.replace("{event_data}", json.dumps(event.data))

            # Queue prompt execution to avoid interrupting an active turn
            from app.core.context import context
            if context.session_id and context.session_id != "default_session" and getattr(context, "_active_turn", False):
                logger.info(f"KLAUSE is currently in active turn. Queueing rule '{rule.rule_id}' prompt.")
                self._react_queue.append(prompt)
            else:
                self._run_proactive_thought(prompt)

    def _run_proactive_thought(self, prompt: str):
        """Runs Gemini think cycle asynchronously to prevent blocking the event thread."""
        import threading
        threading.Thread(target=self._async_think_runner, args=(prompt,), daemon=True).start()

    def _async_think_runner(self, prompt: str):
        from app.core.brain import Brain
        from app.core.context import context
        try:
            # Set turn state
            context._active_turn = True
            brain = Brain()
            logger.info(f"Running proactive thought: '{prompt}'")
            response = brain.think(prompt, session_id="proactive_session")
            logger.info(f"Proactive thought complete. Response: '{response[:200]}...'")
        except Exception as e:
            logger.error(f"Failed to execute proactive thought: {e}")
        finally:
            context._active_turn = False
            # Check queued triggers
            if self._react_queue:
                next_prompt = self._react_queue.pop(0)
                self._run_proactive_thought(next_prompt)


# Singleton instance
rule_engine = RuleEngine()
