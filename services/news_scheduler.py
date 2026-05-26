import threading
from datetime import datetime, timedelta
from typing import Callable


class NewsScheduler:
    def __init__(
        self,
        job: Callable[[], dict],
        *,
        enabled: bool = True,
        interval_minutes: int = 60,
        startup_delay_seconds: int = 15,
        job_label: str = "采集",
    ):
        self.job = job
        self.job_label = job_label
        self.enabled = enabled
        self.interval_minutes = max(5, interval_minutes)
        self.startup_delay_seconds = max(0, startup_delay_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._job_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._state = {
            "enabled": self.enabled,
            "running": False,
            "interval_minutes": self.interval_minutes,
            "last_started_at": None,
            "last_finished_at": None,
            "next_run_at": None,
            "last_count": None,
            "last_message": f"自动{self.job_label}尚未启动",
            "last_error": None,
            "run_count": 0,
        }

    def start(self) -> None:
        if not self.enabled or self._thread:
            return
        self._thread = threading.Thread(target=self._loop, name="worldpulse-news-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def run_now(self, source: str = "manual") -> dict:
        if not self._job_lock.acquire(blocking=False):
            return {"ok": True, "message": f"后台正在{self.job_label}，完成后会自动更新缓存。", "count": 0, "source": source, "busy": True}
        self._mark_running(source)
        return self._run_locked(source)

    def trigger(self, source: str = "manual") -> dict:
        if not self._job_lock.acquire(blocking=False):
            return {"ok": True, "message": f"后台正在{self.job_label}，完成后会自动更新缓存。", "count": 0, "source": source, "busy": True}
        self._mark_running(source)
        thread = threading.Thread(target=self._run_locked, kwargs={"source": source}, name="worldpulse-manual-collect", daemon=True)
        thread.start()
        return {"ok": True, "message": f"已开始后台{self.job_label}。", "count": 0, "source": source, "busy": True}

    def _run_locked(self, source: str) -> dict:
        try:
            result = self.job()
            self._mark_finished(result)
            return {**result, "source": source, "busy": False}
        except Exception as exc:
            result = {"ok": False, "message": f"采集失败: {exc}", "count": 0}
            self._mark_finished(result, error=str(exc))
            return {**result, "source": source, "busy": False}
        finally:
            self._job_lock.release()

    def status(self) -> dict:
        with self._state_lock:
            return dict(self._state)

    def _loop(self) -> None:
        if self._stop_event.wait(self.startup_delay_seconds):
            return
        while not self._stop_event.is_set():
            self.run_now(source="scheduled")
            next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
            with self._state_lock:
                self._state["next_run_at"] = next_run.isoformat()
            self._stop_event.wait(self.interval_minutes * 60)

    def _mark_running(self, source: str) -> None:
        now = datetime.now().isoformat()
        with self._state_lock:
            self._state.update(
                {
                    "running": True,
                    "last_started_at": now,
                    "last_error": None,
                    "last_message": f"正在自动{self.job_label}" if source == "scheduled" else f"正在手动{self.job_label}",
                }
            )

    def _mark_finished(self, result: dict, error: str | None = None) -> None:
        with self._state_lock:
            self._state.update(
                {
                    "running": False,
                    "last_finished_at": datetime.now().isoformat(),
                    "last_count": result.get("count"),
                    "last_message": result.get("message"),
                    "last_error": error,
                    "run_count": int(self._state["run_count"] or 0) + 1,
                }
            )
