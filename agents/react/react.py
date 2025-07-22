import logging
from typing import Any, Callable, Literal, get_origin

from litellm import ContextWindowExceededError
from pydantic import BaseModel

from .utils.ai import dspy, lm
from dspy.primitives.program import Module
from dspy.adapters.types.tool import Tool
from dspy.signatures.signature import ensure_signature
import json

logger = logging.getLogger(__name__)

class ReAct(Module):
    def __init__(self, signature, tools: list[Callable], max_iters=100, strict_iters: int | None = None):
        """
        `tools` is either a list of functions, callable classes, or `dspy.Tool` instances.
        `strict_iters` enforces a fixed number of iterations, overriding `max_iters`.
        """

        self.signature = signature = ensure_signature(signature)
        self.max_iters = max_iters
        self.strict_iters = strict_iters

        tools = [t if isinstance(t, Tool) else Tool(t) for t in tools]
        tools = {tool.name: tool for tool in tools}

        inputs = ", ".join([f"`{k}`" for k in signature.input_fields.keys()])
        outputs = ", ".join([f"`{k}`" for k in signature.output_fields.keys()])
        instr = [f"{signature.instructions}\n"] if signature.instructions else []
        iterations_text = f" after exactly {self.strict_iters} iterations" if self.strict_iters is not None else ""
        pursuit_text = " Unrelentingly pursue the goal and continue to improve with each iteration, making the most of every step. Do not stop. Take diverse exploration and revision paths that are different from your previous paths. Do your best to improve performance on the task with each step, even if it seems complete!" if self.strict_iters is not None else ""
        instr.extend([
            f"You will be given {inputs} and your goal is to finish with {outputs}{iterations_text}.{pursuit_text}\n",
            "To do this, you will interleave Thought, Tool Name, and Tool Args, and receive a resulting Observation.\n",
            "Thought can reason about the current situation, and Tool Name can be the following types:\n",
        ])

        if self.strict_iters is None:
            tools["finish"] = Tool(
                func=lambda **kwargs: "Completed.",
                name="finish",
                desc=f"Signals that the final outputs, i.e. {outputs}, are now available and marks the task as complete.",
                args={},
            )

        for idx, tool in enumerate(tools.values()):
            args = getattr(tool, "args")
            desc = (f", whose description is <desc>{tool.desc}</desc>." if tool.desc else ".").replace("\n", "  ")
            desc += f" It takes arguments {args} in JSON format."
            instr.append(f"({idx+1}) {tool.name}{desc}")

        react_signature = (
            dspy.Signature({**signature.input_fields}, "\n".join(instr))
            .append("trajectory", dspy.InputField(), type_=str)
            .append("next_thought", dspy.OutputField(), type_=str)
            .append("next_tool_name", dspy.OutputField(), type_=Literal[tuple(tools.keys())])
            .append("next_tool_args", dspy.OutputField(), type_=dict[str, Any])
        )

        fallback_signature = dspy.Signature(
            {**signature.input_fields, **signature.output_fields},
            signature.instructions,
        ).append("trajectory", dspy.InputField(), type_=str)

        self.tools = tools
        self.react = dspy.Predict(react_signature)
        self.extract = dspy.ChainOfThought(fallback_signature)

    def _format_trajectory(self, trajectory: dict[str, Any]):
        adapter = dspy.settings.adapter or dspy.ChatAdapter()
        trajectory_signature = dspy.Signature(f"{', '.join(trajectory.keys())} -> x")
        return adapter.format_user_message_content(trajectory_signature, trajectory)

    def forward(self, **input_args):
        trajectory = {}
        num_iters = self.strict_iters if self.strict_iters is not None else self.max_iters

        for idx in range(num_iters):
            pred = self._call_with_potential_trajectory_truncation(self.react, trajectory, **input_args)

            trajectory[f"thought_{idx}"] = pred.next_thought
            trajectory[f"tool_name_{idx}"] = pred.next_tool_name
            trajectory[f"tool_args_{idx}"] = pred.next_tool_args

            try:
                parsed_tool_args = {}
                tool = self.tools[pred.next_tool_name]
                for k, v in pred.next_tool_args.items():
                    if hasattr(tool, "arg_types") and k in tool.arg_types:
                        arg_type = tool.arg_types[k]
                        if isinstance((origin := get_origin(arg_type) or arg_type), type) and issubclass(
                            origin, BaseModel
                        ):
                            parsed_tool_args[k] = arg_type.model_validate(v)
                            continue
                    parsed_tool_args[k] = v
                trajectory[f"observation_{idx}"] = self.tools[pred.next_tool_name](**parsed_tool_args)
            except Exception as e:
                trajectory[f"observation_{idx}"] = f"Failed to execute: {e}"
                logger.error(f"Failed to execute: {e}")

            # print(f"Language Model: {lm}")
            print(f"LM History: {lm.history[-1].get('usage', None)}")
            logger.info(f"<ITERATION #{idx} DETAILS>\n")
            logger.info(f"<TOKENS>")
            logger.info(f"Input Tokens: {lm.history[-1].get('usage', {}).get('prompt_tokens', None)}")
            logger.info(f"Output Tokens: {lm.history[-1].get('usage', {}).get('completion_tokens', None)}")
            logger.info(f"Total Tokens: {lm.history[-1].get('usage', {}).get('total_tokens', None)}")
            logger.info(f"</TOKENS>")
            logger.info(f"<HISTORY>")
            dspy.inspect_history(n=1)
            logger.info(f"</HISTORY>")
            logger.info(f"</ITERATION #{idx} DETAILS>")
                
            if self.strict_iters is None and pred.next_tool_name == "finish":
                break

        # Print full LM history with all nested levels
        history_str = str(lm.history)
        logger.info(f"Full LM History:\n{history_str}")
        
        extract = self._call_with_potential_trajectory_truncation(self.extract, trajectory, **input_args)
        
        pred = dspy.Prediction(trajectory=trajectory, **extract)
        input_tokens = sum([x.get('usage', {}).get('prompt_tokens', 0) for x in lm.history])
        output_tokens = sum([x.get('usage', {}).get('completion_tokens', 0) for x in lm.history])
        result = {
          'input_tokens': input_tokens,
          'output_tokens': output_tokens,
          'total_tokens': input_tokens + output_tokens,
          'trajectory': pred.trajectory,
          'reasoning': pred.reasoning,
          'completed': pred.completed,
          'result': pred.result,
        }
        for k, v in extract.items():
            result[k] = v

        return json.loads(json.dumps(result, default=str))
    def _call_with_potential_trajectory_truncation(self, module, trajectory, **input_args):
        while True:
            try:
                return module(
                    **input_args,
                    trajectory=self._format_trajectory(trajectory),
                )
            except ContextWindowExceededError:
                logger.warning("Trajectory exceeded the context window, truncating the oldest tool call information.")
                trajectory = self.truncate_trajectory(trajectory)

    def truncate_trajectory(self, trajectory):
        """Truncates the trajectory so that it fits in the context window.

        Users can override this method to implement their own truncation logic.
        """
        keys = list(trajectory.keys())
        if len(keys) < 4:
            # Every tool call has 4 keys: thought, tool_name, tool_args, and observation.
            raise ValueError(
                "The trajectory is too long so your prompt exceeded the context window, but the trajectory cannot be "
                "truncated because it only has one tool call."
            )

        for key in keys[:4]:
            trajectory.pop(key)

        return trajectory

