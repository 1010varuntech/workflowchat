from models.model import *
from fastapi import Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from supertokens_python.recipe.session import SessionContainer
from typing import Optional


def get_workflow_collection(request: Request) :
    return request.app.database["workflows"]

def get_workflow_chat_collection(request: Request) :
    return request.app.database["workflowchats"]

def aman_service_initial() :
    return "hello how are you ?"

def aman_function_to_generate_question() :
    return "this is a new question"

def trigger_workflow_chat(request: Request, workflowId: str) :
    initial_question = aman_service_initial(workflowId)   #will need to send workflow prompt
    workflow_chat = WorkflowChat(
        workflowid=workflowId,
        messages=[WorkflowChatMessage(question=initial_question)]
    )
    workflow_chat_data = jsonable_encoder(workflow_chat)
    new_workflow_chat = get_workflow_chat_collection(request).insert_one(workflow_chat_data)
    if(new_workflow_chat.inserted_id) :
        return {
            "workFlowChatId": new_workflow_chat.inserted_id,
            "question" :initial_question,
        }
    else :
        raise HTTPException(status_code=401, detail="Error while creation of workflow chat")


def continue_workflow_chat(request: Request, chatId: str, user_response: str) :
    workflow_chat = get_workflow_chat_collection(request).find_one({"_id": chatId})
    if not workflow_chat:
        raise HTTPException(status_code=404, detail="Workflow chat not found")
    
    history_messages = workflow_chat["messages"]

    last_message = history_messages[-1]
    last_message["response"] = user_response
    history_messages[-1] = last_message

    next_question, flag = aman_function_to_generate_question(history_messages)

    new_message = WorkflowChatMessage(question=next_question)

    history_messages.append(jsonable_encoder(new_message))
    update_workflow_chat = get_workflow_chat_collection(request).update_one({"_id": chatId}, {"$set": {"messages": history_messages}})

    if update_workflow_chat.modified_count == 0:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "workFlowChatId": chatId,
        "question" : next_question,
    }