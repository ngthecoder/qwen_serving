from pydantic import ConfigDict
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
from fastapi.responses import StreamingResponse
import logging
import json

logging.basicConfig(
    filename="vram.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

def log_vram(label):
    used = torch.cuda.memory_allocated() / 1024**3
    logging.info(f"[VRAM] {label}: {used:.2f} GB")

log_vram("Initialized")

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2-1.5B-Instruct")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa"
)

log_vram("After model load")

app = FastAPI()

class Request(BaseModel):
    message: str
    max_tokens: int

class OpenAIRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    model: str
    messages: list[dict[str, str]]
    stream: bool = True
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = None
    ignore_eos: Optional[bool] = False

@app.get("/ping")
def ping():
    return {
        "text": "pong"
    }

@app.post("/chat/sync")
def sync(request: Request):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": request.message},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=request.max_tokens,
    )

    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return {
        "response": response
    }

def response_streamer(request: Request):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": request.message},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    generation_kwargs = dict(model_inputs, streamer=streamer, max_new_tokens=request.max_tokens)

    thread = Thread(target=model.generate, kwargs=generation_kwargs)

    thread.start()
    
    for i, new_text in enumerate(streamer):
        log_vram(f"During text generation (loop#{i})")
        yield f"data: {new_text}\n\n"
    
    log_vram("After text generation")

@app.post("/chat")
def stream(request: Request):
    return StreamingResponse(response_streamer(request), media_type="text/event-stream")

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

def openai_response_sync(request: OpenAIRequest):
    text = tokenizer.apply_chat_template(
        request.messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=request.max_tokens,
    )

    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return {
        "response": response
    }

def openai_response_streamer(request: OpenAIRequest):
    text = tokenizer.apply_chat_template(
        request.messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    generation_kwargs = dict(model_inputs, streamer=streamer, max_new_tokens=request.max_tokens)

    thread = Thread(target=model.generate, kwargs=generation_kwargs)

    thread.start()
    
    for i, new_text in enumerate(streamer):
        chunk = {"id": "...", "choices": [{"index": 0, "delta": {"content": new_text}, "finish_reason": None}]}
        yield f"data: {json.dumps(chunk)}\n\n"

    last_chunk = {"id": "...", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    yield f"data: {json.dumps(last_chunk)}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
def chat_completion(request: OpenAIRequest):
    if request.stream:
        return StreamingResponse(openai_response_streamer(request), media_type="text/event-stream")
    else:
        # return openai_response_sync(request)
        raise HTTPException(400, "Only streaming is supported")

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)