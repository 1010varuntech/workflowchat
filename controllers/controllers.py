from fastapi import Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from models.model import WorkflowChat, WorkflowChatMessage
from supertokens_python.recipe.session import SessionContainer
import openai
import json
from dotenv import load_dotenv
import os

load_dotenv()

openai.api_key = os.getenv("OPENAI_KEY")

def get_workflow_collection(request: Request):
    return request.app.database["workflows"]

def get_workflow_chat_collection(request: Request):
    return request.app.database["workflowchats"]

def generate_initial_prompt():
    return ("Hello! I'm excited to help you generate leads using LinkedIn Sales Navigator. To get started, could you tell me what industry or sector you're targeting for your lead generation? For example, are you looking for leads in Technology, Finance, Healthcare, or another field?")

def generate_follow_up_question(context):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are a lead generation assistant for LinkedIn Sales Navigator.
                    Your tasks are to:
                    1. Collect user requirements for lead generation by asking a series of structured questions.
                    2. Ask follow-up questions to clarify user needs and ensure complete information.
                    3. Map user responses to the allowed LinkedIn Sales Navigator categories. Use the reference mapping provided below to validate and convert user responses into acceptable categories.
                    4. Handle invalid responses by providing examples and re-asking questions until valid responses are received.
                    5. Allow users to modify parameters if they request changes by updating the existing data.
                    6. Keep track of all collected information and ask for any missing details to complete the lead generation criteria.
                    7. Determine if the user wants to finish the process based on their natural language responses. If the user indicates they are done or provides a phrase suggesting completion (e.g., "that's enough"), set 'finished' to true and end the process.
                    Reference mapping for allowed values:
                    - **Industry**: Automotive, Finance, Healthcare, Technology, Education, etc.
                    - **Location**: New York, San Francisco, London, Mumbai, etc.
                    - **CompanySize**: 1-10 employees, 11-50 employees, 51-200 employees, 201-500 employees, 501-1000 employees, 1000+ employees.
                    - **SeniorityLevel**: Intern, Junior, Associate, Manager, Director, VP, C-Level.
                    - **JobFunction**: Sales, Marketing, Engineering, IT, HR, Finance, Customer Support.
                    - **YearsOfExperience**: 0-2 years, 3-5 years, 6-10 years, 11-15 years, 16+ years.
                    - **LinkedInConnections**: 0-100, 101-500, 501-1000, 1001-5000, 5000+.
                    - **SharedExperiences**: Similar projects, Industry-specific experience, Educational background, Previous companies.
                    - **RecentActivity**: Posted about industry trends, Engaged with posts, Shared articles, Commented on discussions.
                    Example Mapping:
                    - For **Industry**: If the user responds with "car manufacturing", map to "Automotive".
                    - For **Location**: If the user says "companies near Mumbai, India", map to "Mumbai".
                    - For **CompanySize**: If the user mentions "close to 500 employees", map to "201-500 employees".
                    - For **SeniorityLevel**: If the user specifies "manager", map to "Manager".
                    - For **JobFunction**: If the user indicates "IT", map to "IT".
                    - For **YearsOfExperience**: If the user says "5 years", map to "3-5 years" if necessary for precision.
                    - For **LinkedInConnections**: If the user mentions "over 1000 connections", map to "1001-5000".
                    - For **SharedExperiences**: If the user refers to "similar projects", map to "Similar projects".
                    - For **RecentActivity**: If the user says "recently posted about industry trends", map to "Posted about industry trends".
                    When a response is invalid, provide the user with specific examples from the mapping list and ask them to provide a valid response. Confirm all parameters with the user and request any additional details as needed. Maintain a smooth conversation flow and ensure the user can update their inputs if necessary. End the process when the user indicates they are finished.
                    """
                },
                {
                    "role": "system",
                    "content": """
                    The user may provide responses that need to be mapped to allowed values. Your response should:
                    1. Validate user input against the allowed values specified in the reference mapping.
                    2. Provide examples of valid responses if the input is invalid, using the reference mapping as a guide.
                    3. Confirm the parameters with the user and request any additional details if needed to ensure accurate lead generation criteria.
                    4. Handle requests to change parameters by updating the existing data based on user feedback.
                    5. Maintain the conversation flow by asking the next relevant question from the list of required parameters.
                    6. Determine if the user wants to finish the process based on their responses. If the user indicates they are done (e.g., "that's enough", "finish", "no more details"), set 'finished' to true and conclude the interaction.
                    """
                },
                *context
            ],
            functions=[
                {
                    "name": "update_lead_info",
                    "description": "Update or add lead generation parameters based on user input.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "parameter": {"type": "string", "description": "The parameter to update or add"},
                            "value": {"type": "string", "description": "The mapped value for the parameter"},
                            "valid": {"type": "boolean", "description": "Whether the input is valid"},
                            "message": {"type": "string", "description": "Message to display to the user"},
                            "next_question": {"type": "string", "description": "Next question to ask the user"},
                            "finished": {"type": "boolean", "description": "Whether the user wants to finish the process"}
                        },
                        "required": ["parameter", "value", "valid", "message", "next_question", "finished"]
                    }
                }
            ],
            function_call={"name": "update_lead_info"}
        )
        if hasattr(response.choices[0].message, 'function_call'):
            result = json.loads(response.choices[0].message['function_call']['arguments'])
            return result
        else:
            raise HTTPException(status_code=400, detail="No function call found in the response")
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
    
def save_workflow_chat_to_json(chat_id: str, data: dict):
    filename = f"lead_generation_requirements_{chat_id}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def trigger_workflow_chat(request: Request, workflowId: str):
    initial_question = generate_initial_prompt()
    workflow_chat = WorkflowChat(
        workflowid=workflowId,
        messages=[WorkflowChatMessage(question=initial_question)],
        collected_info={}
    )
    workflow_chat_data = jsonable_encoder(workflow_chat)
    new_workflow_chat = get_workflow_chat_collection(request).insert_one(workflow_chat_data)
    if new_workflow_chat.inserted_id:
        return {
            "workFlowChatId": str(new_workflow_chat.inserted_id),
            "question": initial_question,
        }
    else:
        raise HTTPException(status_code=401, detail="Error while creating workflow chat")
    
def continue_workflow_chat(request: Request, chatId: str, user_response: str):
    workflow_chat = get_workflow_chat_collection(request).find_one({"_id": chatId})
    if not workflow_chat:
        raise HTTPException(status_code=404, detail="Workflow chat not found")
    workFlowId = workflow_chat["workflowid"]
    history_messages = workflow_chat["messages"]
    collected_info = workflow_chat.get("collected_info", {})
    last_message = history_messages[-1]
    last_message["response"] = user_response
    history_messages[-1] = last_message
    context = [{"role": "assistant", "content": message["question"]} for message in history_messages]
    context.append({"role": "user", "content": user_response})
    result = generate_follow_up_question(context)
    if result['valid']:
        collected_info[result['parameter']] = result['value']
        new_message = WorkflowChatMessage(question=result['next_question'])
        history_messages.append(jsonable_encoder(new_message))
        update_data = {
            "messages": history_messages,
            "collected_info": collected_info
        }
        if result['finished']:
            update_data["is_completed"] = True
            json_filename = save_workflow_chat_to_json(chatId, collected_info)
            update_data["json_filename"] = json_filename
        update_workflow_chat = get_workflow_chat_collection(request).update_one(
            {"_id": chatId},
            {"$set": update_data}
        )
        if update_workflow_chat.modified_count == 0:
            raise HTTPException(status_code=404, detail="Workflow chat not found")
        response = {
            "workFlowChatId": chatId,
            "question": result['next_question'],
        }
        if result['finished']:
            # response["message"] = "Workflow completed. JSON file saved."
            # response["json_filename"] = json_filename
            workFlow = get_workflow_collection(request).find_one({"_id": workFlowId})
            return workFlow
        return response
    else:
        raise HTTPException(status_code=400, detail=result['message'])