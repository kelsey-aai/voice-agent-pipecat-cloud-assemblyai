# Pipecat voice agent on AssemblyAI, deployed to Pipecat Cloud

Companion repo for [How to build and deploy a voice agent using Pipecat and AssemblyAI](https://www.assemblyai.com/blog/building-a-voice-agent-with-pipecat).

- **Speech-to-text:** AssemblyAI STT 3.7 Realtime Agent (`assemblyai-stt-3-7-realtime-agent`) through `AssemblyAISTTService`, or the Sync API (`universal-3-6-pro`) through `AssemblyAISyncSTTService` when `STT_MODE=sync`.
- **LLM:** OpenAI GPT-4o.
- **Text-to-speech:** AssemblyAI text-to-speech (`assemblyai-tts-1`, voice `aai-kyla`) through `AssemblyAITTSService`.
- Live transcript logging from the context aggregators (`on_user_turn_stopped`, `on_assistant_turn_stopped`).

| File | What it does |
|------|--------------|
| `bot.py` | The agent. `bot(runner_args)` is the entry point for the local runner and Pipecat Cloud. |
| `requirements.txt` | `pipecat-ai` with the AssemblyAI, OpenAI, Silero, Daily, runner and WebRTC extras |
| `Dockerfile` | Pipecat Cloud image on `dailyco/pipecat-base` |
| `pcc-deploy.toml` | Agent name, secret set, profile and scaling for `pipecat cloud deploy` |
| `.env.example` | The environment variables `bot.py` reads |

## Pipecat version

Use the first `pipecat-ai` release after 1.16.0. It includes pipecat-ai/pipecat#6752, which treats `assemblyai-stt-3-7-realtime-agent` as a Universal-3 Pro family model. On 1.16.0 the model string is sent, but the service drops `agent_context`, `voice_focus`, `mode` and `language_codes`, and refuses `vad_force_turn_endpoint=False`.

## Run locally

```bash
git clone https://github.com/kelsey-aai/voice-agent-pipecat-cloud-assemblyai
cd voice-agent-pipecat-cloud-assemblyai
uv venv && uv pip install -r requirements.txt
cp .env.example .env   # add your keys
uv run bot.py          # open http://localhost:7860/client and click Connect
```

Set `STT_MODE=sync` in `.env` to try the Sync API instead of streaming.

## Deploy to Pipecat Cloud

```bash
uv tool install "pipecat-ai[cli]" --with pipecatcloud
pipecat cloud auth login
pipecat cloud secrets set my-voice-agent-secrets --file .env
pipecat cloud deploy
pipecat cloud project start my-voice-agent --use-daily
```

`pipecat cloud deploy` builds the image from the `Dockerfile` in the cloud. If you build and push your own image instead, build it for `linux/arm64`.
