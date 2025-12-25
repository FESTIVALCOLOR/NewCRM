# -*- coding: utf-8 -*-
"""
Модели SQLAlchemy для CRM Supervision - для добавления в server/database.py
"""

# ДОБАВИТЬ В server/database.py после модели StageExecutor:

class SupervisionCard(Base):
    __tablename__ = "supervision_cards"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    column_name = Column(String, nullable=False, default='Новый заказ')
    deadline = Column(Date, nullable=True)
    tags = Column(Text, nullable=True)

    # Менеджеры
    senior_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    dan_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # ДАН (Дизайнер авторского надзора)
    dan_completed = Column(Boolean, default=False)

    # Приостановка
    is_paused = Column(Boolean, default=False)
    pause_reason = Column(Text, nullable=True)
    paused_at = Column(DateTime, nullable=True)

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contract = relationship("Contract", back_populates="supervision_card")
    senior_manager = relationship("Employee", foreign_keys=[senior_manager_id])
    dan = relationship("Employee", foreign_keys=[dan_id])


# ТАКЖЕ ДОБАВИТЬ в модель Contract relationship:
# supervision_card = relationship("SupervisionCard", back_populates="contract", uselist=False)
