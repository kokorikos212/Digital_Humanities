import os
import openai
import json 

from tools import all_tool_definitions, tool_handlers


DEEPSEEK_KEY = json.load(open(os.path.join(os.path.dirname(__file__), "database/", "envariables.json")))["DEEPSEEK_KEY"]  

client = openai.OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

def run_pipeline(user_prompt, system_prompt="You are a helpful assistant."):
    ling_handler = tool_handlers["linguistic"](output_dir="output/graphs")
    file_handler = tool_handlers["writer"](folder_path="output")

    tool_map = {
        "get_tags": ling_handler.get_tags,
        "generate_viz": ling_handler.generate_viz,
        "write_file": file_handler.write_file,
        # Safety net for common LLM hallucinations:
        "visualize_syntax": ling_handler.generate_viz 
    }
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    iterations = 0
    max_iterations = 30

    while iterations < max_iterations:
        iterations += 1
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=all_tool_definitions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # If there are no more tool calls, the LLM has finished its task
        if not tool_calls:
            return response_message.content

        # Add the assistant's request to the conversation history
        messages.append(response_message)
        
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            print(f"DEBUG [Iter {iterations}]: LLM called {func_name}")
            
            if func_name in tool_map:
                try:
                    result = tool_map[func_name](**args)
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
            else:
                result = f"Error: Tool {func_name} is not registered."

            # Append the result to messages so the LLM sees it in the next loop
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result) 
            })

    return "Max iterations reached without a final answer."


system_prompt = json.load(open(os.path.join(os.path.dirname(__file__), "database", "system_prompt.json")))["system_prompt"]
# print(f"System Prompt: {system_prompt}\n")  
# system_prompt = "You are a sarcastic weather reporter who hates rain."
prompt = json.load(open(os.path.join(os.path.dirname(__file__), "database", "prompts.json")))["ex_file"]
# prompt = "You cannot use the tools i have provided the schema for. Try to understand why this is the case.'"
response = run_pipeline(prompt, system_prompt=system_prompt) 
print(response)


