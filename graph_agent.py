import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from testingguardrail import querying
from kbhelper import is_out_of_knowledge_base
from dspyrag.ver5 import ask_question,provide_feedback


load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
serpapi_key = os.getenv("SERPAPI_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=api_key,
    temperature=0.7,
    model_kwargs={"streaming": False}
)


class ChatState(BaseModel):
    input: str
    output: Optional[str] = ""
    ismath: bool = False
    llmcheckmath:bool= False
    score: float = 0.0
    counter:int=0
    is_present_in_kb:bool=False
    relevntdoc: str = ""
    web_search_results: str = ""
    


def input_filter_agent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"Check if this query is math-focused (algebra, geometry, etc.): {state.input}. Respond with 'yes' or 'no'."
    )
    ismath, score = querying(state.input)
    
    llmcheckmath = "yes" in response.content.lower()
    
    if llmcheckmath or ismath:
        result = f"✅ Allowed: {state.input} (Similarity: {score:.3f})"
    else:
        result = f"❌ Blocked. Not a math query: {state.input} (Similarity: {score:.3f})"
    
    return ChatState(
        input=state.input,
        output=result,
        counter=state.counter + 1,
        ismath=ismath,
        llmcheckmath=llmcheckmath,
        score=score
    )
def checkifitsmath(state: ChatState) -> str:
    return "MathQuery" if state.llmcheckmath or state.ismath else "Non_Math_Query"
def notmathquery(state: ChatState) -> ChatState:
    reasons = []
    
    if not state.llmcheckmath:
        reasons.append("LLM flagged it as not math")
    if not state.ismath:
        reasons.append("Embedding similarity below threshold")
    
    reason_text = "; ".join(reasons) if reasons else "No reason specified"
    
    return ChatState(
        input=state.input,
        output=f"🚫 Query filtered out. Reason: {reason_text} (Similarity: {state.score:.3f})",
        counter=state.counter + 1,
        ismath=state.ismath,
        llmcheckmath=state.llmcheckmath,
        score=state.score
    )
def checkifinkb(state: ChatState) -> str:
    return "INKB" if state.is_present_in_kb else "NotINKB"
        

def handlemathquery(state: ChatState) -> ChatState:
    is_outside_kb, docs,score = is_out_of_knowledge_base(state.input)
    print(is_outside_kb)
    
    retrieved_snippets = ""
    if (is_outside_kb):
        state.relevntdoc=ask_question(question=state.input)
        print(state.relevntdoc)
   
    
    return ChatState(
        input=state.input,
        output=f" Input:\n{state.input}\n\n📚 KB Coverage: { is_outside_kb} \n score:{score}",
        counter=state.counter + 1,
        ismath=state.ismath,
        llmcheckmath=state.llmcheckmath,
        score=state.score,
        is_present_in_kb=is_outside_kb,
        
        relevntdoc=retrieved_snippets
    )
def Retrievalagent(state: ChatState) -> ChatState:
    prompt = f"""
You are a smart document cleaning and correction agent specialized in mathematics.

Below is a set of raw chunks retrieved from a knowledge base in response to the query:
"{state.input}"

Your task is to:
- Fix OCR errors, spelling, grammar, and formatting issues
- Remove noise (page numbers, headers, question indices like (i), (ii), 12., etc.)
- Preserve mathematical expressions, definitions, formulas, and key explanations
- Ensure the cleaned content is coherent, readable, and relevant to the query
- Do **not** explain your changes — just return the cleaned text

Output only the cleaned and corrected content.

Retrieved Chunks:
{state.relevntdoc}
"""
    response = llm.invoke(prompt)

    return ChatState(
        input=state.input,
        output=response.content[:400],
        counter=state.counter + 1,
        is_present_in_kb=state.is_present_in_kb,
        ismath=state.ismath,
        llmcheckmath=state.llmcheckmath,
        score=state.score,
        relevntdoc=str(response.content)
    )


import requests

def webRetrievalagent(state: ChatState) -> ChatState:
    try:
        params = {
            "engine": "google",
            "q": f"{state.input} mathematics tutorial explanation",
            "api_key": serpapi_key,
            "num": 5,
            "hl": "en",
            "gl": "us"
        }

        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        search_data = response.json()
        organic_results = search_data.get("organic_results", [])
        search_results = []

        for i, result in enumerate(organic_results[:3]):
            title = result.get("title", "No title provided")
            snippet = result.get("snippet", "No snippet available")
            link = result.get("link", "No link available")

            search_results.append(
                f"""🔍 Result {i+1}:
📌 Title: {title}
📄 Snippet: {snippet}
🔗 Link: {link}
"""
            )

        web_search_content = "\n".join(search_results)
        print(web_search_content)

        return ChatState(
            input=state.input,
            output=f"🌐 Web search retrieved {len(search_results)} relevant results.",
            counter=state.counter + 1,
            web_search_results=web_search_content,
            is_present_in_kb=state.is_present_in_kb
        )

    except Exception as e:
        return ChatState(
            input=state.input,
            output=f"❌ Web search failed: {str(e)}",
            counter=state.counter + 1,
            web_search_results="",
            is_present_in_kb=state.is_present_in_kb
        )

def solutionGenerator(state: ChatState) -> ChatState:
    llmresponse=""
    if state.is_present_in_kb:
        prompt = f"""
You are a brilliant math professor helping a student understand a problem step by step.

Here is the student’s question:
"{state.input}"

Below are retrieved materials from your knowledge base that might help:
{state.relevntdoc}

Your job is to:
- Read the retrieved context
- Solve the student's question in a detailed, step-by-step manner
- If helpful, cite relevant equations or definitions from the context
- Make your explanation simple and educational, like a teacher explaining to a high school or undergraduate student
- Do not say "based on the context" or refer to the documents—just give the answer as if it’s your own

Return only the final cleaned step-by-step answer.
""" 
        llmresponse = llm.invoke(prompt).content
    else:
        prompt=f"""You are a brilliant math professor helping a student with a math problem.

Here is the student’s question:
"{state.input}"

You couldn't find the answer in your notes, so you searched the web. Below are the top results:

{state.web_search_results}

Your job is to:
- Read and interpret the titles and snippets like a human browsing the web
- Infer the full explanation as if you had clicked and read those articles
- Provide a full step-by-step solution to the question
- Include any relevant formulas, definitions, or concepts (e.g., derivatives, integration rules, etc.)
- Make your explanation simple and educational, like a teacher explaining to a high school or undergraduate student
- Explain clearly and simply, like a teacher helping a student understand for the first time

Do **not** mention the source links or say “based on web search.” Just explain confidently and fully.

Return only the cleaned, final answer.

"""
        llmresponse=llm.invoke(prompt).content
       
       
    
    return ChatState(
        input=state.input,
        output=llmresponse,
        counter=state.counter + 1,
        )    
def positive():
    provide_feedback(True)
def Negative():
    provide_feedback(False)




graph_builder = StateGraph(ChatState)
graph_builder.add_node("classify_math_query", input_filter_agent)
graph_builder.add_node("handle_math_query", handlemathquery)
graph_builder.add_node("handle_non_math_query", notmathquery)
graph_builder.add_node("Retrievalagent",Retrievalagent)
graph_builder.add_node("webRetrieval",webRetrievalagent)
graph_builder.add_node("SolutionGenerator",solutionGenerator)

graph_builder.set_entry_point("classify_math_query")

graph_builder.add_conditional_edges("classify_math_query", checkifitsmath, {
    "MathQuery": "handle_math_query",
    "Non_Math_Query": "handle_non_math_query"
})
graph_builder.add_conditional_edges("handle_math_query",checkifinkb,{
    "INKB":"Retrievalagent","NotINKB":"webRetrieval"
})
graph_builder.add_edge("Retrievalagent","SolutionGenerator")

graph_builder.add_edge("webRetrieval","SolutionGenerator")

graph_builder.add_edge("SolutionGenerator",END)


graph = graph_builder.compile()

try:
    with open("workflow.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    import webbrowser
    webbrowser.open("file://" + os.path.abspath("workflow.png"))
except Exception as e:
    print("Error:", e)
