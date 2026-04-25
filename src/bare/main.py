from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
import logging
import json
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2-1.5B-Instruct")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa"
)

app = FastAPI()

# --- Schemas ---
class TextContentPart(BaseModel):
    type: Literal["text"]
    text: str

class Message(BaseModel):
    role: str
    content: Union[str, List[TextContentPart]]

class OpenAIRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    model: str
    messages: List[Message]
    stream: bool = True
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = None
    ignore_eos: Optional[bool] = False

# --- Helpers ---
def normalize_messages(messages: List[Message]) -> List[dict]:
    """
    OpenAI spec allows `content` to be either a string or a list of content
    parts (for multimodal inputs). Qwen's chat template only handles strings,
    so we flatten any list-form content into a single string by concatenating
    all text parts.
    """
    normalized = []
    for message in messages:
        if isinstance(message.content, list):
            text = "".join(part.text for part in message.content)
            normalized.append({"role": message.role, "content": text})
        else:
            normalized.append({"role": message.role, "content": message.content})
    return normalized

# --- Exception handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation error at {request.url.path}")
    logger.error(f"Errors: {exc.errors()}")
    logger.error(f"Body: {body.decode()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body.decode()}
    )


# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"text": "pong"}

@app.get("/v1/models")
def models():
    return {
        "object": "list",
        "data": [
            {
                "id": "Qwen/Qwen2-1.5B-Instruct",
                "object": "model",
                "created": 0,
                "owned_by": "local"
            }
        ]
    }

def openai_response_streamer(req: OpenAIRequest):
    normalized = normalize_messages(req.messages)

    text = tokenizer.apply_chat_template(
        normalized,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer, skip_prompt=True, skip_special_tokens=True
    )

    generation_kwargs = dict(
        model_inputs,
        streamer=streamer,
        max_new_tokens=req.max_tokens
    )

    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    for new_text in streamer:
        chunk = {
            "id": "...",
            "choices": [
                {"index": 0, "delta": {"content": new_text}, "finish_reason": None}
            ]
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    last_chunk = {
        "id": "...",
        "choices": [
            {"index": 0, "delta": {}, "finish_reason": "stop"}
        ]
    }
    yield f"data: {json.dumps(last_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
def chat_completion(req: OpenAIRequest):
    if req.stream:
        return StreamingResponse(
            openai_response_streamer(req),
            media_type="text/event-stream"
        )
    else:
        raise HTTPException(400, "Only streaming is supported")

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)