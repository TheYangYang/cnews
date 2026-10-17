"""Speech synthesis helpers: GPU gate and Opus encoding."""

from realtime_ingestion.tts.gpu_gate import GpuGate
from realtime_ingestion.tts.opus import encode_opus_from_wav, write_wav_from_samples

__all__ = ["GpuGate", "encode_opus_from_wav", "write_wav_from_samples"]
