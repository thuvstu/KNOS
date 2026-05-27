# backend/app/services/embedding.py
import asyncio
import time
from typing import Optional
from uuid import UUID
import structlog

logger = structlog.get_logger()


class EmbeddingService:
    """Gemini Embedding API + レート制限付き非同期キュー"""

    def __init__(self, api_key: str, model: str, dimension: int, max_rpm: int = 10):
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.max_rpm = max_rpm
        self._queue: asyncio.Queue[tuple[UUID, str]] = asyncio.Queue()
        self._running = False
        self._rpm_timestamps: list[float] = []

    async def start(self):
        """バックグラウンドワーカー起動"""
        self._running = True
        asyncio.create_task(self._worker())
        logger.info("embedding_service_started", model=self.model)

    async def stop(self):
        self._running = False

    def enqueue(self, entry_id: UUID, text: str):
        self._queue.put_nowait((entry_id, text))
        logger.info("embedding_queued", entry_id=str(entry_id), queue_size=self._queue.qsize())

    async def generate(self, text: str) -> Optional[list[float]]:
        """テキストからEmbeddingを生成（直接呼び出し用）"""
        if not self.api_key:
            logger.warning("embedding_skipped_no_api_key")
            return None

        self._wait_rate_limit()

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            result = genai.embed_content(
                model=f"models/{self.model}",
                content=text,
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.dimension,
            )
            vector = result["embedding"]
            logger.info("embedding_generated", dim=len(vector))
            return vector
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            return None

    def _wait_rate_limit(self):
        now = time.monotonic()
        self._rpm_timestamps = [t for t in self._rpm_timestamps if now - t < 60]
        if len(self._rpm_timestamps) >= self.max_rpm:
            sleep_time = 60 - (now - self._rpm_timestamps[0]) + 0.1
            if sleep_time > 0:
                logger.warning("rate_limit_approaching", remaining_rpm=0, sleep_sec=sleep_time)
                time.sleep(sleep_time)
        self._rpm_timestamps.append(now)

    async def _worker(self):
        from ..database import AsyncSessionLocal
        from ..models.entry import Embedding
        from sqlalchemy import select

        while self._running:
            try:
                entry_id, text = await asyncio.wait_for(self._queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            start = time.monotonic()
            try:
                vector = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: asyncio.run(self._sync_generate(text))
                )
                if vector is None:
                    raise ValueError("Embedding generation returned None")

                async with AsyncSessionLocal() as session:
                    existing = await session.get(Embedding, entry_id)
                    if existing:
                        existing.vector = vector
                        existing.input_text = text
                        existing.model = self.model
                    else:
                        session.add(Embedding(
                            entry_id=entry_id,
                            vector=vector,
                            model=self.model,
                            input_text=text,
                        ))
                    await session.commit()

                ms = int((time.monotonic() - start) * 1000)
                logger.info("embedding_completed", entry_id=str(entry_id), duration_ms=ms)

            except Exception as e:
                logger.error("embedding_worker_error", entry_id=str(entry_id), error=str(e))
            finally:
                self._queue.task_done()

    async def _sync_generate(self, text: str) -> Optional[list[float]]:
        return await asyncio.get_event_loop().run_in_executor(None, lambda: self._blocking_generate(text))

    def _blocking_generate(self, text: str) -> Optional[list[float]]:
        if not self.api_key:
            return None
        self._wait_rate_limit()
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            result = genai.embed_content(
                model=f"models/{self.model}",
                content=text,
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.dimension,
            )
            return result["embedding"]
        except Exception as e:
            logger.error("embedding_blocked_failed", error=str(e))
            return None


# Singleton
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        from ..config import get_settings
        s = get_settings()
        _service = EmbeddingService(
            api_key=s.gemini_api_key,
            model=s.embedding_model,
            dimension=s.embedding_dimension,
            max_rpm=s.embedding_max_rpm,
        )
    return _service
