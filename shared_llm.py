import os
os.environ["HF_HOME"] = r"C:\PetalHF"
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

print("Loading shared Qwen 0.5B engine...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16
)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

print("Shared Qwen engine ready.")


def generate(messages, max_new_tokens=250, temperature=0.7):
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]

    return tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    ).strip()


def write_text(request):
    messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's writing engine. "
                "Write clear, natural, useful text. "
                "Follow the user's requested format and tone."
            )
        },
        {
            "role": "user",
            "content": request
        }
    ]

    return generate(
        messages,
        max_new_tokens=250,
        temperature=0.7
    )


def reason(request):
    messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's reasoning engine. "
                "Answer questions clearly, accurately, and simply. "
                "Do not invent facts. "
                "Give useful explanations appropriate to the user's question."
            )
        },
        {
            "role": "user",
            "content": request
        }
    ]

    return generate(
        messages,
        max_new_tokens=250,
        temperature=0.7
    )