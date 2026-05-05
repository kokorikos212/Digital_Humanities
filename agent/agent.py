import openai
import json 

from toolset import linguistic_tools
from toolset import linguisticTools

from tools_to_write import write_tools
from tools_to_write import FolderRestrictedAgent 



# Merge all tools into one list for the LLM
tools = linguistic_tools + write_tools

DEEPSEEK_KEY = json.load(open("config.json"))["DEEPSEEK_KEY"]  

client = openai.OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

def run_pipeline(user_prompt, system_prompt="..."):
    # 1. Initialize all toolkits
    ling_handler = linguisticTools() 
    file_handler = FolderRestrictedAgent(folder_path="output")
    
    # 2. Centralized Dispatcher Map
    # Key: The name the LLM sees | Value: The actual method to run
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
        tools=tools, # Combined list from both suites
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


system_prompt = json.load(open("system_prompt.json"))["system_prompt"]
print(f"System Prompt: {system_prompt}\n")  
# system_prompt = "You are a sarcastic weather reporter who hates rain."
prompt = """Create a markdown report summarizing the linguistic features of the following text: "Maya and Patrick had an apointment at the cafe, but it was canceled due to the rain." Include tokenization, POS tags, and named entities. Save the report using the write_file tool."""
response = run_pipeline(prompt, system_prompt=system_prompt) 
print(response)


