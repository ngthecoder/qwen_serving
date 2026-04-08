import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2-1.5B-Instruct")

AutoTokenizer.from_pretrained(MODEL_NAME)

AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa"
)