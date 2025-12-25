# -*- coding: utf-8 -*-
"""
Модели SQLAlchemy для CRM карточек - для добавления в server/database.py
"""

# ДОБАВИТЬ В server/database.py после модели Contract:

class CRMCard(Base):
    __tablename__ = "crm_cards"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    column_name = Column(String, nullable=False)  # Колонка Kanban (Новый заказ, В работе и т.д.)
    deadline = Column(Date, nullable=True)
    tags = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)

    # Менеджеры и исполнители
    senior_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    sdp_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    gap_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    surveyor_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Дополнительные поля (добавлены через миграции)
    approval_deadline = Column(Date, nullable=True)
    approval_stages = Column(Text, nullable=True)  # JSON строка
    project_data_link = Column(Text, nullable=True)
    tech_task_file = Column(Text, nullable=True)
    tech_task_date = Column(Date, nullable=True)
    survey_date = Column(Date, nullable=True)

    # Метаданные
    order_position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contract = relationship("Contract", back_populates="crm_card")
    senior_manager = relationship("Employee", foreign_keys=[senior_manager_id])
    sdp = relationship("Employee", foreign_keys=[sdp_id])
    gap = relationship("Employee", foreign_keys=[gap_id])
    manager = relationship("Employee", foreign_keys=[manager_id])
    surveyor = relationship("Employee", foreign_keys=[surveyor_id])
    stage_executors = relationship("StageExecutor", back_populates="crm_card", cascade="all, delete-orphan")


class StageExecutor(Base):
    __tablename__ = "stage_executors"

    id = Column(Integer, primary_key=True, index=True)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"), nullable=False)
    stage_name = Column(String, nullable=False)  # Название стадии (Планировка, Визуализация и т.д.)
    executor_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Даты
    assigned_date = Column(DateTime, default=datetime.utcnow)
    deadline = Column(Date, nullable=True)
    submitted_date = Column(DateTime, nullable=True)  # Когда исполнитель сдал работу
    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime, nullable=True)

    # Relationships
    crm_card = relationship("CRMCard", back_populates="stage_executors")
    executor = relationship("Employee", foreign_keys=[executor_id])
    assigner = relationship("Employee", foreign_keys=[assigned_by])


# ТАКЖЕ ДОБАВИТЬ в модель Contract relationship:
# crm_card = relationship("CRMCard", back_populates="contract", uselist=False)
