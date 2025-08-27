import os

from langchain_google_genai import ChatGoogleGenerativeAI
from query.query_db import search_db


def generate_chat_response(query: str, retrieved_docs) -> str:
    """Generate a chat-like response using retrieved documents as context."""

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

    # Create the prompt for the LLM
    system_prompt = """You are a helpful assistant for the TIPQIC project. Use the provided context to answer questions accurately and helpfully. 

        Guidelines:
        - Answer based primarily on the provided context
        - Add information from your background knowledge to fill in the gaps
        - Be conversational and helpful
        - Cite sources when possible (mention page numbers or document names)
        - If asked about something not in the context, politely explain the limitation
    """

    user_prompt = f"""Context from documents (may be empty):
    {context}

    User question:
    {query}

    Instructions:
    - First try to answer using the context above.
    - If the context is insufficient, answer using your general knowledge.
    - If you used background knowledge, clearly note this.
    - Cite document sources only when they appear in the context.
    """

    try:
        # Initialize the chat model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
            system_instruction=system_prompt,
        )

        # Prepend system prompt manually
        composed_prompt = f"""[SYSTEM INSTRUCTION]
        {system_prompt}

        [USER MESSAGE]
        {user_prompt}
        """

        # Generate response
        response = llm.invoke(
            composed_prompt
        )  # Gemini doesn't use system messages the same way

        return response.content

    except Exception as e:
        return f"Error generating response: {e}"


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
            chat_response = generate_chat_response(query, results)

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
