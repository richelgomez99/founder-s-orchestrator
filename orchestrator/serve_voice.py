# serve_voice.py
#
# Upload this to the Lightning Studio and run it there to serve the merged
# founder LoRA as an OpenAI-compatible endpoint. The orchestrator calls it:
#   - voice.py   -> POST /v1/chat/completions   (founder-voice phrasing)
#   - anomaly.py -> POST /v1/chat/completions    (typicality 0..100 fallback)
#
# Auth: OpenAI-style clients send "Authorization: Bearer <token>". LitServe's
# built-in LIT_SERVER_API_KEY checks the X-API-Key header instead, which the
# OpenAI flow does not send, so we implement authorize() to read the bearer
# token directly and also accept X-API-Key. Pick a long random VOICE_BEARER.
#
# Run in the Studio terminal:
#   pip install litserve litgpt
#   export VOICE_BEARER="pick-a-long-random-string"
#   python serve_voice.py
#
# Then expose port 8000 in the Studio and read its public URL:
#   https://8000-YOUR_SUBDOMAIN.cloudspaces.litng.ai
# Local orchestrator env:
#   VOICE_BASE_URL   = https://8000-YOUR_SUBDOMAIN.cloudspaces.litng.ai/v1
#   VOICE_TOKEN      = the VOICE_BEARER you set
#   ANOMALY_BASE_URL = same base + /v1   (optional, for the learned plane)
#   ANOMALY_TOKEN    = same VOICE_BEARER

import os

import litserve as ls
from litserve.specs.openai import ChatMessage
from litgpt import LLM

MERGED = os.environ.get(
    "FOUNDER_LORA_DIR",
    "/teamspace/studios/this_studio/out/founder-phi2-lora/final",
)
BEARER = os.environ.get("VOICE_BEARER", "").strip()  # empty = open (no auth)

# The LoRA was trained with the Alpaca instruction template. Inference MUST use
# the same template or the model falls out of distribution and loops. No system
# prompt: the founder voice lives in the LoRA weights, not in instructions.
ALPACA = (
    "Below is an instruction that describes a task. Write a response that "
    "appropriately completes the request.\n\n### Instruction:\n{instr}\n\n### Response:\n"
)


class FounderVoiceAPI(ls.LitAPI):
    def setup(self, device):
        # Loads the merged LoRA weights produced by litgpt merge_lora.
        self.llm = LLM.load(MERGED)

    def decode_request(self, request, context=None):
        # With OpenAISpec, request is a ChatCompletionRequest pydantic model.
        # Be defensive: accept a dict too, in case the spec shape changes.
        messages = getattr(request, "messages", None)
        if messages is None and isinstance(request, dict):
            messages = request.get("messages", [])
        # Use the last user message as the instruction (the request text). Any
        # system message is ignored on purpose; the voice is in the weights.
        instr = ""
        for m in (messages or []):
            role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
            content = (m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")) or ""
            if role == "user":
                instr = content
        return ALPACA.format(instr=instr.strip())

    def predict(self, prompt, context=None):
        # Greedy and short. The training outputs are one to three sentences, so a
        # small budget plus the Response template keeps it from rambling.
        text = self.llm.generate(prompt, max_new_tokens=64, temperature=0.0, top_k=1)
        # Cut at the first template marker if the model keeps going.
        for stop in ("\n### ", "\n\n", "### Instruction"):
            idx = text.find(stop)
            if idx != -1:
                text = text[:idx]
        yield text.strip()

    def encode_response(self, output, context=None):
        for tok in output:
            yield ChatMessage(role="assistant", content=tok)


if __name__ == "__main__":
    # OpenAI-compatible spec, passed to the API (the non-deprecated way).
    api = FounderVoiceAPI(spec=ls.OpenAISpec())
    # If a bearer was set, enable LitServe's built-in API-key auth. The
    # orchestrator clients send both Authorization: Bearer and X-API-Key, so
    # either header matches. Leave VOICE_BEARER empty to run open for testing.
    if BEARER:
        os.environ["LIT_SERVER_API_KEY"] = BEARER
    server = ls.LitServer(api, accelerator="auto")
    server.run(port=8000, generate_client_file=False)
