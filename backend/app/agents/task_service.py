from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import WorkflowState
from app.agents.workflow import get_workflow
from app.models import AgentTask, Repository
from app.models.agent_task import TaskStatus, TaskType

logger = structlog.get_logger(__name__)


class AgentTaskService:
    """Service for creating and running agent workflow tasks."""

    async def create_task(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        request_type: str,
        user_request: str,
    ) -> AgentTask:
        """Create a new AgentTask record in the database."""
        task_type_map = {
            "repository_qa": TaskType.repository_qa,
            "investigation": TaskType.investigation,
            "security": TaskType.security_scan,
            "documentation": TaskType.documentation,
        }
        task_type = task_type_map.get(request_type, TaskType.repository_qa)

        task = AgentTask(
            user_id=user_id,
            repository_id=repository_id,
            task_type=task_type,
            status=TaskStatus.queued,
            plan={"user_request": user_request, "request_type": request_type},
            token_budget=0,
            tokens_used=0,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        logger.info("AgentTask created", task_id=str(task.id), task_type=task_type)
        return task

    async def run_task(
        self,
        db: AsyncSession,
        task_id: uuid.UUID,
    ) -> dict:
        """Run the LangGraph workflow for a task and persist the result."""
        # Load task
        result_obj = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = result_obj.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Load repository for context
        repo_result = await db.execute(select(Repository).where(Repository.id == task.repository_id))
        repo = repo_result.scalar_one_or_none()

        user_request = (task.plan or {}).get("user_request", "")
        request_type = (task.plan or {}).get("request_type", "repository_qa")

        # Mark task as running
        task.status = TaskStatus.running
        await db.commit()

        # Build initial workflow state
        initial_state: WorkflowState = {
            "task_id": str(task.id),
            "user_id": str(task.user_id),
            "repository_id": str(task.repository_id),
            "branch": repo.selected_branch if repo else "main",
            "commit_sha": "",
            "user_request": user_request,
            "request_type": request_type,
            "plan": {},
            "retrieved_evidence": [],
            "tool_results": [],
            "agent_outputs": {},
            "token_budget": 4000,
            "tokens_used": 0,
            "service_constraints": [],
            "errors": [],
            "warnings": [],
            "final_result": None,
            "task_status": "running",
        }

        # Execute workflow
        try:
            workflow = get_workflow(db=db)
            final_state: WorkflowState = await workflow.ainvoke(initial_state)

            final_result = final_state.get("final_result") or {}
            task_status_str = final_state.get("task_status", "completed")

            status_map = {
                "completed": TaskStatus.completed,
                "partial": TaskStatus.partial,
                "failed": TaskStatus.failed,
                "paused": TaskStatus.paused,
            }
            task.status = status_map.get(task_status_str, TaskStatus.completed)
            task.result = final_result
            task.tokens_used = final_state.get("tokens_used", 0)
            task.token_budget = final_state.get("token_budget", 4000)
            task.completed_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(
                "AgentTask completed",
                task_id=str(task.id),
                status=task_status_str,
                tokens_used=task.tokens_used,
            )
            return final_result

        except Exception as exc:
            logger.error("AgentTask execution failed", task_id=str(task.id), error=str(exc))
            task.status = TaskStatus.failed
            task.result = {"error": str(exc)}
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise

    async def get_task(self, db: AsyncSession, task_id: uuid.UUID) -> AgentTask | None:
        result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[AgentTask]:
        result = await db.execute(
            select(AgentTask)
            .where(AgentTask.user_id == user_id)
            .order_by(AgentTask.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
