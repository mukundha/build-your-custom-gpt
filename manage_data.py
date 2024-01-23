import os 
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import AstraDB
from astrapy.db import AstraDBCollection
import chainlit as cl
from chainlit.types import AskFileResponse
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.docstore.document import Document

ASTRA_DB_API_ENDPOINT = os.environ["ASTRA_DB_API_ENDPOINT"] 
ASTRA_DB_APPLICATION_TOKEN = os.environ["ASTRA_DB_APPLICATION_TOKEN"]

embeddings = OpenAIEmbeddings()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

user_collection = AstraDBCollection(
        collection_name="user_documents",
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_APPLICATION_TOKEN,
    )

vstore = AstraDB(
        embedding=embeddings,
        collection_name="astra_vector_demo",
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_APPLICATION_TOKEN,
    )
welcome_message = """Welcome to the Build your own Custom GPT demo! To get started:
1. Upload a PDF or text file
2. Ask a question about the file
"""


def process_file(content, filename, filetype):
    app_user = cl.user_session.get("user")
    username = app_user.username 
    import tempfile    
    if filetype == "text/plain":
        Loader = TextLoader
    elif filetype == "application/pdf":
        Loader = PyPDFLoader

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tempfile:
        if filetype == "text/plain":
            tempfile.write(content)
        elif filetype == "application/pdf":
            with open(tempfile.name, "wb") as f:
                f.write(content)

        loader = Loader(tempfile.name)
        docs = loader.load_and_split(text_splitter=text_splitter)        
        for doc in docs:
            doc.metadata["source"] = f"{filename}"
            doc.metadata["username"] = f"{username}"
        return docs

def get_docsearch(content, filename, filetype):
    docs = process_file(content, filename, filetype)    
    cl.user_session.set("docs", docs)
    user = cl.user_session.get("dbuser")    
    vstore.add_documents(docs)    
    user["files"].append(f"{filename}")
    user_collection.update_one(filter={"username": f"{user['username']}"}, update={"$set": {"files": user['files']}}) 
    return vstore

def get_files_for_user(username):
    collection = AstraDBCollection(
        collection_name="user_documents",
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_APPLICATION_TOKEN,
    )
    user = collection.find_one({"username": f"{username}"})
    cl.user_session.set("dbuser", user["data"]["document"])
    return user["data"]["document"]

async def upload_new_file():
    app_user = cl.user_session.get("user")  
    username = app_user.username   
    files = await cl.AskFileMessage(
                    content=welcome_message,
                    accept=["application/pdf"],
                    max_size_mb=20,
                    timeout=180,                    
    ).send()
    file = files[0]
    msg = cl.Message(
            content=f"Processing `{file.name}`...",             
    )
    await msg.send()  
    
    dbuser = cl.user_session.get('dbuser')
    if not dbuser: 
        newuser = {"username": f"{username}", 
                   "files": [f"{file.name}"]}
        user_collection.insert_one(newuser)
        user=user_collection.find_one({"username": f"{username}"})
        cl.user_session.set("dbuser", user["data"]["document"])

    text = file.content
    await cl.make_async(get_docsearch)(text, file.name, file.type)
    msg.content = f"Processing done. You can now ask questions!"
    await msg.update()
