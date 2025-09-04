import os
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from .query_db import search_db
# Create Serper tool (NEW ADDITION)
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.tools import Tool
import os


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
    try:
        # Build context string (same as your code)
        context_parts = []
        for doc, score in retrieved_docs:
            source_info = f"Source: {doc.metadata.get('source', 'Unknown')}"
            if "page" in doc.metadata:
                source_info += f", Page: {doc.metadata['page']}"
            context_parts.append(f"{source_info}\n{doc.page_content}")
        context = "\n\n".join(context_parts)

        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.0)

        # Create tools and bind to LLM
        try:
            from langchain_core.tools import tool
            from langchain_community.utilities import GoogleSerperAPIWrapper
            import os
            
            # Initialize Serper API client
            SERPER_API_KEY = os.getenv("SERPER_API_KEY")
            serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)
            
            # Wrap as a LangChain tool
            @tool(description="Search the web for current, real-time, or specific information if context and knowledge are insufficient.")
            def serper_search(query: str) -> str:
                result = serper.run(query)
                print(f"🔹 Serper returned: {result[:300]}...")  # preview first 300 chars
                return result
            
            # Bind tool to LLM
            llm_with_tools = llm.bind_tools([serper_search])
            print("✅ Serper search tool bound to LLM")
        except ImportError:
            print("❌ Serper API not available, using LLM directly")
            llm_with_tools = llm


        user_prompt = f"""You are a helpful assistant for the TIPQIC project. You have access to:
1. Provided context from TIPQIC documents
2. Your internal knowledge
3. Web search tool for additional information

Follow this three-stage approach:

STAGE 1 – Context-First:
- Use ONLY the provided context to answer
- If context is sufficient, give a complete answer
- Cite sources (e.g., page numbers, document names) where possible
- If context is missing details, explicitly state:
  "The provided context does not include information about <topic>."

STAGE 2 – Internal Knowledge Fallback:
- If context is insufficient or missing, provide an additional answer from your internal knowledge
- Clearly separate with phrases like:
  "Based on the provided context..." vs. "Additionally, from general knowledge..."

STAGE 3 – Web Search Fallback:
- If both context and internal knowledge are insufficient, you MUST use the web search tool
- Call the search tool with a specific query to get current information
- Combine information from all three sources
- Clearly separate with phrases like:
  "Based on the provided context..." vs. "From general knowledge..." vs. "From web search results..."

IMPORTANT: If you need current, real-time, or specific information that's not in the context or your knowledge, you MUST use the search tool. Do not just mention that you can search - actually perform the search.

Context:
{context}

Question: {query}"""

        # Use bind_tools approach - LLM handles tool execution automatically
        print("🚀 Calling LLM with tools...")
        try:
            # Single LLM call - handles tool execution automatically
            response = llm_with_tools.invoke(user_prompt)
            print(f"📊 Response type: {type(response)}")
            print(f"📊 Response content: {response.content}")
            
            # Check if tools were called (for debugging)
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 Tool calls detected: {len(response.tool_calls)}")
                for tool_call in response.tool_calls:
                    print(f"   - Tool: {tool_call['name']}")
                    print(f"   - Args: {tool_call['args']}")
            else:
                print("ℹ️ No tool calls made")
            
            print("✅ LLM completed successfully")
            return response.content
            
        except Exception as e:
            print(f"❌ LLM failed: {e}")
            return f"Error: {e}"

    except Exception as e:
        return f"Error generating response: {e}"


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
