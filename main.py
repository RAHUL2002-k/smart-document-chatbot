#Import libraries
from langchain_community.vectorstores import Chroma
from langchain_community.llms import OpenAI
from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
import streamlit as st

# Constants
VECTORDB_DIR = "chroma_db"
OPENAI_API_KEY = "your_openai_api_key_here"  # Replace with your OpenAI API key

# Initialize OpenAI LLM and embeddings
llm = OpenAI(model_name='gpt-4o-mini', temperature=0.1)
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Streamlit app title
st.title("Document Chatbot 🚀")

# Sidebar for file upload and configuration
with st.sidebar:
    st.header("Configuration")
    file_path = st.text_input("Enter the path to your file:")
    file_type = st.selectbox("Select the file type:", ["csv", "pdf", "txt"])
    if st.button("Create Vector Database"):
        if file_path and file_type:
            with st.spinner("Creating vector database..."):
                # Load documents
                if file_type == "csv":
                    loader = CSVLoader(file_path=file_path, source_column="prompt")
                elif file_type == "pdf":
                    loader = PyPDFLoader(file_path=file_path)
                elif file_type == "txt":
                    loader = TextLoader(file_path=file_path)
                documents = loader.load()

                # Chunk documents
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
                chunks = text_splitter.split_documents(documents)
                st.write(f"Split {len(documents)} documents into {len(chunks)} chunks.")

                # Create vector database
                vectordb = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=VECTORDB_DIR)
                vectordb.persist()
                st.success("Vector database created successfully!")
        else:
            st.error("Please provide a valid file path and type.")

# Main chat interface
st.header("Chat with Your Document")

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User input
user_input = st.chat_input("Ask a question...")

if user_input:
    # Add user question to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Display user question
    with st.chat_message("user"):
        st.write(user_input)

    # Load vector database and create QA chain
    vectordb = Chroma(persist_directory=VECTORDB_DIR, embedding_function=embeddings)
    retriever = vectordb.as_retriever(search_kwargs={"k": 5, "score_threshold": 0.7})
    prompt_template = """
    Given the following context and a question, generate an answer based on this context only.
    In the answer, try to provide as much text as possible from the "response" section in the source document context without making many changes.
    If the answer is not found in the context, kindly state "I don't know." Don't try to make up an answer.

    CONTEXT: {context}

    QUESTION: {question}
    """
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, input_key="query", return_source_documents=True, chain_type_kwargs={"prompt": PROMPT})

    # Generate response
    with st.spinner("Thinking..."):
        response = qa_chain(user_input)

    # Add bot response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response["result"]})

    # Display bot response
    with st.chat_message("assistant"):
        st.write(response["result"])
        st.write("Source Documents:", response["source_documents"])
