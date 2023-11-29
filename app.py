from typing import List, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
import chainlit as cl
from manage_data import vstore, get_files_for_user, upload_new_file

@cl.oauth_callback
def oauth_callback(
    default_app_user: cl.AppUser,
) -> Optional[cl.AppUser]:  
    return default_app_user

@cl.on_chat_start
async def on_chat_start():
    app_user = cl.user_session.get("user")
    await cl.Message(f"Hello {app_user.username}").send()    
    user = get_files_for_user(app_user)    
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
    chain = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0, streaming=True),
        chain_type="stuff",        
        retriever=vstore.as_retriever(
            search_kwargs=
                {"filter": {"username": f"{app_user.username}"},"k": 5}),
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

    text_elements = []  # type: List[cl.Text]
    # Optional Code to Add the source documents to the message
    if source_documents:
        for source_idx, source_doc in enumerate(source_documents):
            source_name = f"source_{source_idx}"
            # Create the text element referenced in the message
            text_elements.append(
                cl.Text(content=source_doc.page_content, name=source_name)
            )
        source_names = [text_el.name for text_el in text_elements]
        if source_names:
            answer += f"\nSources: {', '.join(source_names)}"
        else:
            answer += "\nNo sources found"
    await cl.Message(content=answer, elements=text_elements).send()