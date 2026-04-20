"""
winscript.async_engine — Async/Await Execution Engine

Provides concurrent execution support for WinScript using asyncio.

Usage:
    # In WinScript:
    async tell Chrome
        navigate to "https://example.com"
    end tell
    
    async tell Excel
        set cell "A1" to "Data"
    end tell
    
    await  -- Wait for all async operations
"""

import asyncio
from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from winscript.ast_nodes import TellBlock
from winscript.context import ExecutionContext
from winscript.runtime import WinScriptRuntime


@dataclass
class AsyncTask:
    """Represents an async operation."""
    task_id: str
    tell_block: TellBlock
    context: ExecutionContext
    future: asyncio.Future
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Exception = None


class AsyncEngine:
    """
    Async execution engine for WinScript.
    
    Manages concurrent operations and provides await/sync capabilities.
    """
    
    def __init__(self, runtime: WinScriptRuntime):
        self.runtime = runtime
        self.tasks: dict[str, AsyncTask] = {}
        self.task_counter = 0
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create the event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        self.task_counter += 1
        return f"task_{self.task_counter}"
    
    def submit_async(self, tell_block: TellBlock, context: ExecutionContext) -> str:
        """
        Submit a tell block for async execution.
        
        Returns a task ID that can be used to await the result.
        """
        task_id = self._generate_task_id()
        loop = self._get_loop()
        future = loop.create_future()
        
        task = AsyncTask(
            task_id=task_id,
            tell_block=tell_block,
            context=context,
            future=future,
            status="pending"
        )
        self.tasks[task_id] = task
        
        # Start execution in thread pool
        self.executor.submit(self._execute_async_task, task)
        
        return task_id
    
    def _execute_async_task(self, task: AsyncTask):
        """Execute an async task in the thread pool."""
        try:
            task.status = "running"
            # Execute the tell block
            self.runtime._exec_tell(task.tell_block, task.context)
            task.status = "completed"
            task.result = task.context.return_value
            
            # Set future result
            loop = self._get_loop()
            asyncio.run_coroutine_threadsafe(
                self._set_future_result(task.future, task.result),
                loop
            )
        except Exception as e:
            task.status = "failed"
            task.error = e
            
            # Set future exception
            loop = self._get_loop()
            asyncio.run_coroutine_threadsafe(
                self._set_future_exception(task.future, e),
                loop
            )
    
    async def _set_future_result(self, future: asyncio.Future, result: Any):
        """Set future result (must be called in event loop)."""
        if not future.done():
            future.set_result(result)
    
    async def _set_future_exception(self, future: asyncio.Future, exc: Exception):
        """Set future exception (must be called in event loop)."""
        if not future.done():
            future.set_exception(exc)
    
    def await_task(self, task_id: str | None = None, timeout: float | None = None) -> Any:
        """
        Wait for async task(s) to complete.
        
        Args:
            task_id: Specific task to await, or None for all pending tasks
            timeout: Maximum time to wait in seconds
        
        Returns:
            The result of the awaited task(s)
        """
        if task_id:
            # Wait for specific task
            if task_id not in self.tasks:
                raise ValueError(f"Task '{task_id}' not found")
            
            task = self.tasks[task_id]
            if task.status in ("completed", "failed"):
                return task.result
            
            # Wait for future
            loop = self._get_loop()
            try:
                result = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(task.future, timeout=timeout),
                    loop
                ).result()
                return result
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task '{task_id}' timed out")
        else:
            # Wait for all pending tasks
            pending_tasks = [
                t for t in self.tasks.values()
                if t.status in ("pending", "running")
            ]
            
            if not pending_tasks:
                return None
            
            loop = self._get_loop()
            futures = [t.future for t in pending_tasks]
            
            try:
                results = asyncio.run_coroutine_threadsafe(
                    asyncio.gather(*[asyncio.wait_for(f, timeout=timeout) for f in futures], return_exceptions=True),
                    loop
                ).result()
                
                # Update task statuses
                for i, task in enumerate(pending_tasks):
                    task.result = results[i]
                    task.status = "completed" if not isinstance(results[i], Exception) else "failed"
                
                return results
            except asyncio.TimeoutError:
                raise TimeoutError("Async operations timed out")
    
    def execute_parallel(self, tell_blocks: list[TellBlock], context: ExecutionContext) -> list[Any]:
        """
        Execute multiple tell blocks in parallel.
        
        Returns:
            List of results from each block
        """
        task_ids = []
        for block in tell_blocks:
            task_id = self.submit_async(block, context)
            task_ids.append(task_id)
        
        # Wait for all to complete
        return self.await_task(timeout=60.0)
    
    def get_task_status(self, task_id: str) -> dict | None:
        """Get the status of a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "id": task.task_id,
            "status": task.status,
            "has_result": task.result is not None,
            "has_error": task.error is not None
        }
    
    def list_tasks(self) -> list[dict]:
        """List all tasks and their statuses."""
        return [
            {
                "id": t.task_id,
                "status": t.status,
                "app": t.tell_block.app_name if t.tell_block else None
            }
            for t in self.tasks.values()
        ]
    
    def cleanup(self):
        """Clean up async resources."""
        self.executor.shutdown(wait=False)
        if self._loop:
            try:
                self._loop.close()
            except Exception:
                pass
