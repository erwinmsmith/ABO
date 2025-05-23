from typing import List, Any, Dict

from AgentDropout.graph.node import Node
from AgentDropout.agents.agent_registry import AgentRegistry
from AgentDropout.llm.llm_registry import LLMRegistry
from AgentDropout.prompt.prompt_set_registry import PromptSetRegistry
from AgentDropout.tools.coding.python_executor import PyExecutor

@AgentRegistry.register('CodeWriting')
class CodeWriting(Node):
    def __init__(self, id: str | None = None, role: str = None, domain: str = "", llm_name: str = ""):
        super().__init__(id, "CodeWriting", domain, llm_name)
        self.llm = LLMRegistry.get(llm_name)
        self.prompt_set = PromptSetRegistry.get(domain)
        self.role = self.prompt_set.get_role() if role is None else role
        self.constraint = self.prompt_set.get_constraint(self.role)
        
    def _process_inputs(self, raw_inputs: Dict[str, str], spatial_info: Dict[str, Dict], temporal_info: Dict[str, Dict], **kwargs) -> List[Any]:
        system_prompt = self.constraint
        spatial_str = ""
        temporal_str = ""
        for id, info in spatial_info.items():
            output = info.get('output', '')
            if output.startswith("```python") and output.endswith("```") and self.role != 'Normal Programmer' and self.role != 'Stupid Programmer':
                code = output.lstrip("```python\n").rstrip("\n```")
                is_solved, feedback, state = PyExecutor().execute(code, self.internal_tests, timeout=10)
                if is_solved and len(self.internal_tests):
                    return "is_solved", code
                spatial_str += f"Agent {id} as a {info['role']}:\n\nThe code written by the agent is:\n\n{output}\n\n Whether it passes internal testing? {is_solved}.\n\nThe feedback is:\n\n {feedback}.\n\n"
            else:
                spatial_str += f"Agent {id} as a {info['role']} provides the following info: {output}\n\n"
        for id, info in temporal_info.items():
            output = info.get('output', '')
            if output.startswith("```python") and output.endswith("```") and self.role != 'Normal Programmer' and self.role != 'Stupid Programmer':
                code = output.lstrip("```python\n").rstrip("\n```")
                is_solved, feedback, state = PyExecutor().execute(code, self.internal_tests, timeout=10)
                if is_solved and len(self.internal_tests):
                    return "is_solved", code
                temporal_str += f"Agent {id} as a {info['role']}:\n\nThe code written by the agent is:\n\n{output}\n\n Whether it passes internal testing? {is_solved}.\n\nThe feedback is:\n\n {feedback}.\n\n"
            else:
                temporal_str += f"Agent {id} as a {info['role']} provides the following info: {output}\n\n"
        user_prompt = f"The task is:\n\n{raw_inputs['task']}\n"
        user_prompt += f"At the same time, the outputs and feedbacks of other agents are as follows:\n\n{spatial_str} \n\n" if spatial_str else ""
        user_prompt += f"In the last round of dialogue, the outputs and feedbacks of some agents were: \n\n{temporal_str}" if temporal_str else ""
        return system_prompt, user_prompt

    def extract_example(self, prompt: str) -> list:
        prompt = prompt['task']
        lines = (line.strip() for line in prompt.split('\n') if line.strip())

        results = []
        lines_iter = iter(lines)
        for line in lines_iter:
            if line.startswith('>>>'):
                function_call = line[4:]
                expected_output = next(lines_iter, None)
                if expected_output:
                    results.append(f"assert {function_call} == {expected_output}")

        return results
    
    def _execute(self, input: Dict[str, str], spatial_info: Dict[str, Any], temporal_info: Dict[str, Any], **kwargs):
        self.internal_tests = self.extract_example(input)
        system_prompt, user_prompt = self._process_inputs(input, spatial_info, temporal_info)
        message = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}]
        response = self.llm.gen(message)
        return response

    async def _async_execute(self, input: Dict[str, str], spatial_info: Dict[str, Any], temporal_info: Dict[str, Any], **kwargs):
        self.internal_tests = self.extract_example(input)
        system_prompt, user_prompt = self._process_inputs(input, spatial_info, temporal_info)
        if system_prompt == "is_solved":
            return user_prompt
        message = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}]
        response = await self.llm.agen(message)
        return response