from typing import List, Dict, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
import chainlit as cl
from manage_data import vstore, get_files_for_user, upload_new_file
from langchain.llms import Bedrock
from langchain.llms import VertexAI

import os 
print('starting app')
llm_provider = os.environ.get("LLM_PROVIDER")
print(llm_provider)

@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.AppUser,
) -> Optional[cl.AppUser]:
  return default_user

@cl.on_chat_start
async def on_chat_start():
    print('started')
    app_user = cl.user_session.get("user")
    print(app_user)
    username =app_user.username
    await cl.Message(f"Hello {username}").send()    
    user = get_files_for_user(username)
    if user:
        await cl.Message(f"Here are your files: {user['files']}. How can i help?").send() 
    else: 
        upload_new_file()
    message_history = ChatMessageHistory()    
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        chat_memory=message_history,
        return_messages=True,
    )  
    llm = None 
    
    if llm_provider == "Bedrock":
        llm = Bedrock(
            credentials_profile_name="default",
            model_id="anthropic.claude-v2:1",
            streaming = True 
        )  
    elif llm_provider == "OpenAI":
        llm = ChatOpenAI(
            model_name="gpt-4-1106-preview", 
            temperature=0, 
            streaming=True)
    elif llm_provider == "Vertex":
        llm = VertexAI(model_name="gemini-pro")
    else:
        raise Exception("LLM Provider not supported")
    
    print("Using LLM provider", llm)

    chain = ConversationalRetrievalChain.from_llm(
        llm = llm ,
        chain_type="stuff",        
        retriever=vstore.as_retriever(
            search_kwargs=
                {"filter": {"username": f"{username}"},"k": 5}),
        memory=memory,
        return_source_documents=True,
    )
    cl.user_session.set("chain", chain)

@cl.on_message
async def main(message: cl.Message):
    chain = cl.user_session.get("chain")  # type: ConversationalRetrievalChain
    cb = cl.AsyncLangchainCallbackHandler()
        
    if message.content.lower().startswith("upload new file"):
        await upload_new_file()        
        return 
    
    res = await chain.acall(message.content, callbacks=[cb])
    answer = res["answer"]
    source_documents = res["source_documents"]  # type: List[Document]
