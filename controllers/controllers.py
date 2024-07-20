from fastapi import Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from models.model import *
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
    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=context,
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
                        "next_question": {"type": "string", "description": "Next question to ask the user"}
                    },
                    "required": ["parameter", "value", "valid", "message", "next_question"]
                }
            }
        ],
        function_call="auto"
    )

    print(response)

    if hasattr(response.choices[0].message, 'function_call'):  # Modified line: Added check for function_call
        result = json.loads(response.choices[0].message['function_call']['arguments'])  # Modified line: Updated the way to access the function call arguments
        return result
    else:
        raise HTTPException(status_code=400, detail="No function call found in the response")

def trigger_workflow_chat(request: Request, workflowId: str):
    initial_question = generate_initial_prompt()
    workflow_chat = WorkflowChat(
        workflowid=workflowId,
        messages=[WorkflowChatMessage(question=initial_question)]
    )
    workflow_chat_data = jsonable_encoder(workflow_chat)
    new_workflow_chat = get_workflow_chat_collection(request).insert_one(workflow_chat_data)
    if new_workflow_chat.inserted_id:
        return {
            "workFlowChatId": new_workflow_chat.inserted_id,
            "question": initial_question,
        }
    else:
        raise HTTPException(status_code=401, detail="Error while creation of workflow chat")

def continue_workflow_chat(request: Request, chatId: str, user_response: str):
    workflow_chat = get_workflow_chat_collection(request).find_one({"_id": chatId})
    if not workflow_chat:
        raise HTTPException(status_code=404, detail="Workflow chat not found")

    history_messages = workflow_chat["messages"]

    last_message = history_messages[-1]
    last_message["response"] = user_response
    history_messages[-1] = last_message

    context = [{"role": "assistant", "content": message["question"]} for message in history_messages]
    context.append({"role": "user", "content": user_response})

    result = generate_follow_up_question(context)

    if result['valid']:
        new_message = WorkflowChatMessage(question=result['next_question'])
        history_messages.append(jsonable_encoder(new_message))
        update_workflow_chat = get_workflow_chat_collection(request).update_one({"_id": chatId}, {"$set": {"messages": history_messages}})

        if update_workflow_chat.modified_count == 0:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {
            "workFlowChatId": chatId,
            "question": result['next_question'],
        }
    else:
        raise HTTPException(status_code=400, detail=result['message'])
