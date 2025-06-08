import asyncio
import websockets
import json
import base64
import sounddevice as sd
import numpy as np
from auralis import TTS, TTSRequest
import tempfile
import os
from typing import Optional
import wave
import io

class TTSServer:
    def __init__(self, tts_model, default_speaker_file: str):
        self.tts = tts_model
        self.default_speaker_file = default_speaker_file
        self.current_playback = None
        self.is_playing = False

    def initialize(self):
        if self.tts is None:
            # Create a new event loop for initialization
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.tts = TTS().from_pretrained(self.model_path, gpt_model=self.gpt_model_path)
            finally:
                loop.close()
        return self

    async def handle_health_check(self, websocket):
        await websocket.send(json.dumps({"type": "health_check", "status": "ok"}))

    def base64_to_wav(self, base64_audio: str) -> str:
        # Decode base64 audio
        audio_data = base64.b64decode(base64_audio)
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.write(audio_data)
        temp_file.close()
        
        return temp_file.name

    async def play_audio(self, audio_data: np.ndarray, sample_rate: int, websocket):
        self.is_playing = True
        await websocket.send(json.dumps({"type": "playback_started"}))
        
        # Calculate total duration
        duration = len(audio_data) / sample_rate
        
        # Start playback
        sd.play(audio_data, sample_rate)
        
        # Monitor playback progress
        start_time = asyncio.get_event_loop().time()
        while sd.get_stream().active:
            current_time = asyncio.get_event_loop().time()
            progress = min(1.0, (current_time - start_time) / duration)
            await websocket.send(json.dumps({
                "type": "playback_in_progress",
                "progress": progress
            }))
            await asyncio.sleep(0.1)
        
        self.is_playing = False
        await websocket.send(json.dumps({"type": "playback_completed"}))

    async def handle_tts_request(self, websocket, message):
        try:
            data = json.loads(message)
            text = data.get("text")
            speaker_file = self.default_speaker_file

            if "speaker_file" in data:
                speaker_file = self.base64_to_wav(data["speaker_file"])

            # Generate speech
            request = TTSRequest(
                text=text,
                speaker_files=[speaker_file]
            )
            
            output = self.tts.generate_speech(request)
            
            # Get audio data
            audio_data = output.to_tensor().numpy()
            sample_rate = output.sample_rate

            # Play audio and monitor progress
            await self.play_audio(audio_data, sample_rate, websocket)

            # Cleanup temporary speaker file if it was created
            if "speaker_file" in data:
                os.unlink(speaker_file)

        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))

    async def handle_waiting(self, websocket):
        while self.is_playing:
            await asyncio.sleep(0.1)

    async def handle_client(self, websocket):
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")

                    if message_type == "health_check":
                        await self.handle_health_check(websocket)
                    elif message_type == "waiting":
                        await self.handle_waiting(websocket)
                    else:
                        await self.handle_tts_request(websocket, message)

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))

        except websockets.exceptions.ConnectionClosed:
            pass

def initialize_tts(model_path: str, gpt_model_path: str):
    """Initialize TTS model before any async operations."""
    # Create a new event loop for initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        tts = TTS()
        # Get the event loop that TTS created
        tts_loop = tts.loop
        # Set it as the current loop
        asyncio.set_event_loop(tts_loop)
        # Initialize the model with CUDA graph support
        return tts.from_pretrained(
            model_path, 
            gpt_model=gpt_model_path,
            enforce_eager=False,  # Disable eager execution to enable CUDA graphs
            use_cuda_graph=True,  # Enable CUDA graph optimization
            scheduler_max_concurrency=10  # Set reasonable concurrency
        )
    finally:
        # Clean up the loop
        loop.close()

async def main(server, host, port):
    # Start WebSocket server
    async with websockets.serve(server.handle_client, host, port):
        print(f"TTS WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()  # run forever 

if __name__ == "__main__":
    # Configuration
    MODEL_PATH = "AstraMindAI/xttsv2"
    GPT_MODEL_PATH = "AstraMindAI/xtts2-gpt"
    DEFAULT_SPEAKER_FILE = "/home/josepheudave/Auralis/audio_samples/default_speaker.wav"
    HOST = "localhost"
    PORT = 9100

    # Initialize TTS model before any async operations
    tts_model = initialize_tts(MODEL_PATH, GPT_MODEL_PATH)
    
    # Initialize server with the pre-initialized model
    server = TTSServer(tts_model, DEFAULT_SPEAKER_FILE)

    # Start the server
    asyncio.run(main(server, HOST, PORT)) 