from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from .query_db import search_db
# Create Serper tool (NEW ADDITION)
from langchain.agents import initialize_agent, Tool
from langchain.schema import SystemMessage

import os
from langchain_community.utilities import GoogleSerperAPIWrapper

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.0)

# Initialize Serper API wrapper
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)

# Wrap Serper as a LangChain Tool
def serper_search(query: str) -> str:
    """Search the web via Serper."""
    result = serper.run(query)
    return result

search_tool = Tool(
    name="WebSearch",
    func=serper_search,
    description="Use this tool to find real-time or specific information if context or internal knowledge is insufficient."
)

# Initialize ReAct agent
tools = [search_tool]
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True,
    handle_parsing_errors=True
)

class TaskList(BaseModel):
    tasks: List[str]


class PromptType(BaseModel):
    type: str  # "normal" or "task"


def classify_prompt(query: str) -> str:
    """Classify if the prompt is asking for tasks or normal response."""
    
    classification_prompt = f"""Classify this user query as either "normal" (for conversational response) or "task" (for actionable tasks).

    Query: {query}
    
    Rules:
    - Use "task" if the query asks for improvements, steps, actions, plans, or how to do something
    - Use "normal" for general questions, explanations, or information requests
    - Keywords like "improve", "enhance", "steps", "how to", "action plan" suggest "task"
    - Keywords like "what is", "explain", "describe", "tell me about" suggest "normal"
    
    Classify this query:"""
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        structured_llm = llm.with_structured_output(PromptType)
        
        result = structured_llm.invoke(classification_prompt)
        return result.type
    except Exception as e:
        # Default to normal if classification fails
        return "normal"


def generate_response_with_routing(query: str, retrieved_docs):
    """Route the query to the appropriate function."""
    
    # Classify the prompt type
    prompt_type = classify_prompt(query)
    
    if prompt_type == "task":
        return generate_chat_tasks(query, retrieved_docs)
    else:
        return generate_chat_response(query, retrieved_docs)


def generate_chat_response(query, retrieved_docs, max_results=5):
    # Build context
    context_parts = []
    for doc, score in retrieved_docs[:max_results]:
        source_info = f"Source: {doc.metadata.get('source','Unknown')}"
        if "page" in doc.metadata:
            source_info += f", Page: {doc.metadata['page']}"
        context_parts.append(f"{source_info}\n{doc.page_content}")
    context = "\n\n".join(context_parts)

    # Construct prompt with context and instructions
    prompt = f"""
You are a helpful assistant for the TIPQIC project. Answer using three stages:

1. Use ONLY the provided context below. Cite sources. If info is missing, state: "The provided context does not include information about <topic>." else say "The provided context includes information about <topic>."
2. If and only if context is insufficient, use your internal knowledge otherwise skip this step.
3. If context and internal knowledge are insufficient, use the WebSearch tool to get real-time information.

Context:
{context}

Question: {query}

Provide your answer clearly, separating information from context, internal knowledge, and web search results.
"""

    # Run agent
    response = agent.run(prompt)
    return response


def generate_chat_tasks(query: str, retrieved_docs) -> TaskList:
    """Generate a structured list of tasks using retrieved documents as context."""

    # Combine the content from retrieved documents
    context_parts = []
    for doc, score in retrieved_docs:
        # Include source information in context
        source_info = f"Source: {doc.metadata.get('source', 'Unknown')}"
        if "page" in doc.metadata:
            source_info += f", Page: {doc.metadata['page']}"

        context_parts.append(f"{source_info}\n{doc.page_content}")

    # Join all context
    context = "\n\n---\n\n".join(context_parts)

    # Create the prompt for task generation
    prompt = f"""Based on the provided context, create a structured list of actionable tasks to address the user's request.

    Context from documents:
    {context}

    User Request: {query}

    Instructions:
    - Generate specific, actionable tasks based on the TIPQIC context
    - Make tasks clear and implementable
    - Focus on practical steps that can be taken
    - Consider TIPQIC-specific processes and best practices
    - Provide 5-10 relevant tasks

    Create a list of tasks that will help address this request."""

    try:
        # Initialize the chat model with structured output
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.3,  # Lower temperature for more consistent structured output
            convert_system_message_to_human=True,
        )

        # Use structured output
        structured_llm = llm.with_structured_output(TaskList)
        response = structured_llm.invoke(prompt)

        return response

    except Exception as e:
        # Fallback to empty task list if structured output fails
        return TaskList(tasks=[f"Error generating tasks: {e}"])


# Update your main function
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python query/chatbot_response.py 'your search query here'")
        print("Example: python query/chatbot_response.py 'What is TIPQIC about?'")
        sys.exit(1)

    # Get the query from command line arguments
    query = " ".join(sys.argv[1:])

    print(f"Question: {query}")
    print("=" * 60)

    try:
        # Search the database
        results = search_db(query)

        if results:
            print("🔍 Found relevant information, generating response...\n")

            # Generate chat response
            chat_response = generate_response_with_routing(query, results)

            print("💬 Response:")
            print(chat_response)

            print("\n" + "=" * 60)
            print("📚 Sources used:")

            for i, (doc, score) in enumerate(results, 1):
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "N/A")
                print(
                    f"{i}. {os.path.basename(source)} (Page {page}) - Relevance: {score:.3f}"
                )

        else:
            print("❌ No relevant documents found in the database.")
            print(
                "💡 Try rephrasing your question or check if the documents are properly indexed."
            )

    except Exception as e:
        print(f"❌ Error during search: {e}")
