from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2-1.5B-Instruct")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa"
)

app = FastAPI()

class Request(BaseModel):
    message: str

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
        max_new_tokens=512,
    )

    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return {
        "response": response
    }

@app.post("/chat")
def stream(request: Request):
    # yet to be developed
    pass

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)