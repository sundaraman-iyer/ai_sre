"""Hugging Face Spaces Entrypoint: SRE Postmortem RAG Assistant with Gradio UI & FastAPI API.

Serves the full FastAPI backend pipeline (RAG, PII Redaction, Injection Guardrails, Upstash Redis Memory)
alongside an interactive web chat interface.
"""

from __future__ import annotations

from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from fastapi import HTTPException

import main

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


async def chat_handler(message: str, history: list[list[str]], session_id: str) -> str:
    """Gradio handler delegating queries to the main FastAPI ask pipeline."""
    if not message or not message.strip():
        return "Please enter a valid question."

    clean_session = session_id.strip() if session_id and session_id.strip() else "hf-space-session"

    try:
        req = main.AskRequest(question=message.strip(), session_id=clean_session)
        response = await main.ask(req)

        answer_text = response.answer
        if response.sources:
            answer_text += "\n\n**Sources Referenced:**\n" + "\n".join(
                f"- `{src}`" for src in response.sources
            )
        if response.pii_redacted:
            answer_text += "\n\n*(Note: PII was detected and redacted from your query)*"

        return answer_text
    except HTTPException as http_err:
        return f"[Error] {http_err.detail}"
    except Exception as err:
        return f"[Unexpected Error] {str(err)}"


# Create interactive Gradio Blocks Interface
with gr.Blocks(title="SRE Postmortem RAG Assistant") as demo:
    gr.Markdown("""
        # SRE Postmortem RAG Assistant
        Query production incident postmortems with **PII Redaction**, **Prompt Injection Defense**,
        **Upstash Redis Multi-turn Memory**, and **Groq LLM Acceleration**.
        """)

    with gr.Row():
        session_input = gr.Textbox(
            label="Session ID (for multi-turn memory)",
            value="default-sre-session",
            placeholder="e.g. incident-response-101",
        )

    chatbot = gr.Chatbot(label="Incident Q&A Assistant", height=450)
    msg_input = gr.Textbox(
        label="Ask a question about SRE postmortems...",
        placeholder="e.g., What caused the outage in the payment service postmortem?",
    )

    with gr.Row():
        submit_btn = gr.Button("Submit Query", variant="primary")
        clear_btn = gr.Button("Clear Chat History")

    gr.Markdown("---")
    gr.Markdown(
        "*FastAPI OpenAPI endpoints available at `/docs` | Powered by LiteLLM, Groq, Upstash Redis & LangSmith*"
    )

    def user_msg(user_message, history):
        return "", history + [[user_message, None]]

    async def bot_reply(history, session_id):
        user_message = history[-1][0]
        bot_response = await chat_handler(user_message, history[:-1], session_id)
        history[-1][1] = bot_response
        return history

    msg_input.submit(user_msg, [msg_input, chatbot], [msg_input, chatbot], queue=False).then(
        bot_reply, [chatbot, session_input], chatbot
    )
    submit_btn.click(user_msg, [msg_input, chatbot], [msg_input, chatbot], queue=False).then(
        bot_reply, [chatbot, session_input], chatbot
    )
    clear_btn.click(lambda: None, None, chatbot, queue=False)

# Mount Gradio Blocks UI onto the main FastAPI app for Hugging Face Spaces
app = gr.mount_gradio_app(app=main.app, blocks=demo, path="/")
