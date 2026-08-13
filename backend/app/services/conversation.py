from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.models.entities import Conversation, TrainingSession
from app.schemas.conversation import ConversationMessageRead, CustomerMessageResponse


class ConversationService:
    MAX_CONTEXT_MESSAGES = 12

    def __init__(self, db: Session) -> None:
        self.db = db

    def history(self, session_id: int) -> list[ConversationMessageRead]:
        messages = (
            self.db.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .order_by(Conversation.id)
            .all()
        )
        return [self._read(message) for message in messages]

    async def talk(self, session: TrainingSession, learner_message: str) -> CustomerMessageResponse:
        learner = Conversation(session_id=session.id, speaker="learner", message=learner_message)
        self.db.add(learner)
        self.db.flush()

        recent = (
            self.db.query(Conversation)
            .filter(Conversation.session_id == session.id)
            .order_by(Conversation.id.desc())
            .limit(self.MAX_CONTEXT_MESSAGES)
            .all()
        )
        recent.reverse()
        context = {
            "scenario": {
                "title": session.scenario.title,
                "business_type": session.scenario.business_type,
                "description": session.scenario.description,
            },
            "customer_profile": session.scenario.customer_profile,
            "performed_steps": session.context.get("performed_steps", []),
            "recent_conversation": [
                {"speaker": item.speaker, "message": item.message} for item in recent
            ],
            "constraints": [
                "只扮演当前客户，不得以教练、考官或系统身份回答。",
                "不得判断柜员操作是否合法或给出规则分数。",
                "不得替学员执行任何柜面操作。",
            ],
        }
        ai_generated = True
        try:
            result = await AgentOrchestrator().run("customer", learner_message, context)
            reply = result.content
        except Exception:
            ai_generated = False
            profile = session.scenario.customer_profile or {}
            reply = profile.get("opening_line", "您好，我想办理这个业务，请告诉我需要提供什么材料。")

        customer = Conversation(session_id=session.id, speaker="customer", message=reply)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(learner)
        self.db.refresh(customer)
        return CustomerMessageResponse(
            learner_message=self._read(learner),
            customer_message=self._read(customer),
            ai_generated=ai_generated,
        )

    @staticmethod
    def recent_context(session: TrainingSession, limit: int = 12) -> list[dict[str, str]]:
        messages = sorted(session.conversations, key=lambda item: item.id)[-limit:]
        return [{"speaker": item.speaker, "message": item.message} for item in messages]

    @staticmethod
    def _read(message: Conversation) -> ConversationMessageRead:
        return ConversationMessageRead(
            id=message.id,
            speaker=message.speaker,
            message=message.message,
            created_at=message.created_at.isoformat(),
        )
