#chroma_client.py

import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings


load_dotenv()  # ⬅️ Loads your .env file

embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

vectorstore = Chroma(
    collection_name="permits",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)
