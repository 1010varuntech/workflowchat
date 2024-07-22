from fastapi import APIRouter, Request, status
from typing import List, Optional
from models.model import *
from controllers.controllers import *
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer
from fastapi import Depends
from pydantic import BaseModel

class ContinueChat(BaseModel) :
    chatId: str
    user_response: str

class ApiResponse(BaseModel):
    workFlowChatId: str
    question: str

router = APIRouter(prefix="/workflowchat", tags=["workflow_chat"])

@router.post("/trigger/{workflowid}", response_description="trigger a workflow chat and return greet message along with chat Id", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)  
def trigger(request: Request, workflowid: str, session: SessionContainer = Depends(verify_session())):
    return trigger_workflow_chat(request, workflowid)

@router.post("/continuechat", response_description="will return the chat Id and the next question", status_code=status.HTTP_200_OK, response_model=ApiResponse)
def continue_chat(request: Request, resp_body: ContinueChat, session: SessionContainer = Depends(verify_session())):
    chatid = resp_body.chatId
    user_response = resp_body.user_response
    return continue_workflow_chat(request, chatid, user_response)
