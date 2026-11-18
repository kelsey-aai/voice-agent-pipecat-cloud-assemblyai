"""Pipecat voice agent on AssemblyAI, ready for Pipecat Cloud.

Speech-to-text: AssemblyAI STT 3.7 Realtime Agent (streaming), or the Sync API
                (Universal-3.6 Pro) when STT_MODE=sync
LLM:            OpenAI GPT-4o
Text-to-speech: AssemblyAI text-to-speech (assemblyai-tts-1, voice Kyla)

Run locally:   uv run bot.py            (opens a WebRTC test page)
Pipecat Cloud: the platform calls bot(runner_args) for every session.
"""

import os

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.assemblyai.stt import AssemblyAISTTService, AssemblyAISyncSTTService
from pipecat.services.assemblyai.tts import AssemblyAITTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.workers.runner import WorkerRunner

load_dotenv(override=True)

SYSTEM_PROMPT = (
    "You are a friendly voice assistant. Keep replies to one or two short "
    "sentences, with no markdown, lists or emoji."
)
GREETING = "Hi, thanks for calling Acme. What's the email on your account?"


def make_stt(session: aiohttp.ClientSession):
    """Streaming STT by default; the Sync API when STT_MODE=sync."""
    if os.getenv("STT_MODE", "streaming") == "sync":
        return AssemblyAISyncSTTService(
            api_key=os.environ["ASSEMBLYAI_API_KEY"],
            aiohttp_session=session,
            settings=AssemblyAISyncSTTService.Settings(model="universal-3-6-pro"),
        )
    return AssemblyAISTTService(
        api_key=os.environ["ASSEMBLYAI_API_KEY"],
        settings=AssemblyAISTTService.Settings(
            model="assemblyai-stt-3-7-realtime-agent",
            mode="balanced",
            agent_context=GREETING,  # seeds context for the first user reply
        ),
        vad_force_turn_endpoint=True,  # Pipecat mode: VAD + Smart Turn own the turn boundary
    )


async def run_bot(transport, session: aiohttp.ClientSession):
    stt = make_stt(session)
    llm = OpenAILLMService(
        api_key=os.environ["OPENAI_API_KEY"],
        settings=OpenAILLMService.Settings(model="gpt-4o"),
    )
    tts = AssemblyAITTSService(
        api_key=os.environ["ASSEMBLYAI_API_KEY"],
        settings=AssemblyAITTSService.Settings(model="assemblyai-tts-1", voice="aai-kyla"),
    )

    context = LLMContext(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Open the call by saying exactly: {GREETING}"},
        ]
    )
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message):
        logger.info(f"user: {message.content}")

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message):
        logger.info(f"assistant: {message.content}")

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,  # feeds each agent reply back to the STT as context
        ]
    )

    worker = PipelineWorker(pipeline, params=PipelineParams())

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Entry point for the Pipecat runner and Pipecat Cloud."""
    transport_params = {
        "daily": lambda: DailyParams(audio_in_enabled=True, audio_out_enabled=True),
        "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    }
    transport = await create_transport(runner_args, transport_params)
    async with aiohttp.ClientSession() as session:
        await run_bot(transport, session)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
