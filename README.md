### Build your own Custom GPT with RAGStack

[RAGStack](https://www.datastax.com/products/ragstack)
- AstraDB
- Langchain
- OpenAI 

### Inspiration

- [Build your own Custom ChatGPTs](https://openai.com/blog/introducing-gpts)
OpenAI allows anyone to create a custom GPT, with their own data. Very cool solution, but proprietary, data is stored and managed by OpenAI. 
- [Astra Assistants API](https://www.datastax.com/blog/introducing-the-astra-assistants-api)
Datastax introduced an implementation of OpenAI's assistant API, that allows developers to easily build custom GPTs. Your data is in your control, stored and managed in your Astra DB account.

### This:
Let developers (businesses) create their own "Build your own custom GPT" solution for their users. 
. 
Solution is Similar to both of the above, but
- you can run a similar service for your users
- demonstrates how you can build such a solution using Astra DB and Langchain (which also means, you have optionality to choose any LLM - for eg, GPT-4 or Claude 2 (via AWS Bedrock) or Gemini-pro (using GCP Vertex) llama (coming soon!) etc..)

### Get started

- [Signup for Astra DB](https://astra.datastax.com/)
- [Recommended] [Enable Preview](https://www.datastax.com/blog/astra-db-serverless-vector-new-experience) for Vector and JSON native experience
- [Refer Google Signin guide](https://developers.google.com/identity/sign-in/web/sign-in#create_authorization_credentials) for Google OAuth credentials, this is used for login to the app.

#### Required environment variables
```
OPENAI_API_KEY=xx
ASTRA_DB_API_ENDPOINT=xxx
ASTRA_DB_APPLICATION_TOKEN=xxx
OAUTH_GOOGLE_CLIENT_ID=xxx
OAUTH_GOOGLE_CLIENT_SECRET=xxx
CHAINLIT_AUTH_SECRET=1234567890

AWS_CREDENTIALS_PROFILE=<aws credentials profile name>


LLM_PROVIDER= ## Bedrock (for Claudev2) or OpenAI (for GPT-4) or Vertex (for GeminiPro)
```

#### Notes on LLM Choice:

##### OpenAI:
- Uses GPT-4 (maybe will make this configurable in future)
- Set `LLM_PROVIDER=OpenAI`
- variable `OPENAI_API_KEY` is sufficient, you can ignore `AWS_CREDENTIALS_PROFILE`

##### Bedrock:
- Uses claude-v2 (maybe will make this configurable in future)
- Set `LLM_PROVIDER=Bedrock`
- variable `AWS_CREDENTIALS_PROFILE` is required, 
- `OPENAI_API_KEY` is required too (used for embeddings, will add optionality in future)


##### Vertex:
- Uses Gemini-pro (maybe will make this configurable in future)
- Set `LLM_PROVIDER=Vertex`
- Run `gcloud auth application-default login` to setup credentials if running locally
- `OPENAI_API_KEY` is required too (used for embeddings, will add optionality in future)
- env variable `AWS_CREDENTIALS_PROFILE` is not required, 

#### Tracing 
To enable tracing with Langsmith, add the following environment variables

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=xxx
LANGCHAIN_PROJECT=xxx
```
#### Run
```
pip install -r requirements.txt

chainlit run app.py
```

### How it works

UI - chainlit

<p float="left">
<img src="images/login.png" width="300px">

<img src="images/upload.png" width="300px">

<img src="images/fileprocess.png" width="300px">

<img src="images/processdone.png" width="300px">

<img src="images/qa.png" width="300px">
</p>

#### Google Login
App is protected with Google Login, after Login `username` returned by Google is used as key to manage user session and data.

#### Loading data for user
After login, user can instruct `upload new file` to upload new files.
- file is split into chunks
- username added to metadata
- stored in AstraDB as a JSON collection

```
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
loader = PyPDFLoader(filename)
docs = loader.load_and_split(text_splitter=text_splitter)        

for doc in docs:
    doc.metadata["source"] = f"{file.name}"
    doc.metadata["username"] = f"{app_user.username}"

vstore = AstraDB(
        embedding=embeddings,
        collection_name="astra_vector_demo",
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_APPLICATION_TOKEN,
    )
vstore.add_documents(docs)
```
That's it! 

<img src="images/documents.png">

#### Chat with your Data

Uses `langchain` to create a conversational chain,
Note: Metadata filtering is used to search only in the documents this user has uploaded.

```
chain = ConversationalRetrievalChain.from_llm(
        llm,
        chain_type="stuff",        
        retriever=vstore.as_retriever(
            search_kwargs=
                {"filter": {"username": f"{app_user.username}"},"k": 5}),
        memory=memory,
        return_source_documents=True,
    )
```

