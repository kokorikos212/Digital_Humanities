import os
import openai
import json 

from tools import all_tool_definitions, tool_handlers


DEEPSEEK_KEY = json.load(open(os.path.join(os.path.dirname(__file__), "database/.gitignore", "envariables.json")))["DEEPSEEK_KEY"]  

client = openai.OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

def run_pipeline(user_prompt, system_prompt="You are a helpful assistant that can analyze text and write markdown reports."):
    # Pass the pre-built schemas directly to the LLM
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_prompt}],
        tools=all_tool_definitions,
        tool_choice="auto"
    )
    
    # Initialize handlers only when needed
    ling_handler = tool_handlers["linguistic"]()
    file_handler = tool_handlers["writer"](folder_path="output/graphs")

    # This map links the LLM function name to the actual method
    tool_map = {
        "get_linguistic_annotations": ling_handler.get_linguistic_annotations,
        "write_file": file_handler.write_file
    }
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # First LLM call to decide tool use
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=all_tool_definitions,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # DYNAMIC CALLING
            if func_name in tool_map:
                print(f"[EXECUTE] {func_name} with {args}")
                result = tool_map[func_name](**args)
            else:
                result = f"Error: Tool {func_name} is not registered in the tool_map."

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result) 
            })
        
        # Final LLM call to summarize results
        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        return final_response.choices[0].message.content

    return response_message.content


system_prompt = json.load(open(os.path.join(os.path.dirname(__file__), "database", "system_prompt.json")))["system_prompt"]
print(f"System Prompt: {system_prompt}\n")  
# system_prompt = "You are a sarcastic weather reporter who hates rain."
# prompt = json.load(open(os.path.join(os.path.dirname(__file__), "database", "prompts.json")))["ex_visualization"]
prompt = "Create a file with the content of an analysis of the following text: 'The cat sat on the mat. The dog barked loudly.' Include a dependency parse visualization and named entity recognition in the report."
response = run_pipeline(prompt, system_prompt=system_prompt) 
print(response)


