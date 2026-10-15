"""Агентын өгөгдлийн төрлүүд ба тогтмолууд."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

TicketType = Literal["Incident", "Service Request", "Access", "Security", "Хамааралгүй"]
Decision = Literal["Хариулах", "Шилжүүлэх", "Татгалзах", "Тодруулах"]
Team = Literal[
    "Service Desk (L1)",
    "Системийн баг (L2)",
    "Сүлжээний баг (L2)",
    "Мэдээллийн аюулгүй байдал (L2)",
    "Хэрэглээний программ (L2)",
    "Хамааралгүй",
]
Level = Literal["Өндөр", "Дунд", "Бага"]
Location = Literal["Төв оффис", "Дархан", "Эрдэнэт", "Баянзүрх", "Тодорхойгүй"]
# Major incident-ийг илрүүлэхэд ашиглах үйлчилгээний ангилал
Service = Literal[
    "branch_connectivity", "vpn_client", "core_system", "loan_system", "email", "meet",
    "printer", "password", "network", "endpoint", "access", "security", "other",
]
Priority = Literal["P1", "P2", "P3", "P4"]

TICKET_TYPES = ["Incident", "Service Request", "Access", "Security", "Хамааралгүй"]
DECISIONS = ["Хариулах", "Шилжүүлэх", "Татгалзах", "Тодруулах"]
TEAMS = [
    "Service Desk (L1)", "Системийн баг (L2)", "Сүлжээний баг (L2)",
    "Мэдээллийн аюулгүй байдал (L2)", "Хэрэглээний программ (L2)", "Хамааралгүй",
]
PRIORITIES = ["P1", "P2", "P3", "P4"]
STATUSES = [
    "Шинэ", "Шийдвэрлэсэн", "L2-т шилжсэн", "Зөвшөөрөл хүлээж буй",
    "Татгалзсан", "Тодруулга хүлээж буй", "Хаагдсан",
]
OPEN_STATUSES = ["Шинэ", "L2-т шилжсэн", "Зөвшөөрөл хүлээж буй", "Тодруулга хүлээж буй"]

L1 = "Service Desk (L1)"
SYS = "Системийн баг (L2)"
NET = "Сүлжээний баг (L2)"
SEC = "Мэдээллийн аюулгүй байдал (L2)"
APP = "Хэрэглээний программ (L2)"


@dataclass
class Ticket:
    id: str
    message_id: str
    channel: str
    masked_text: str
    summary: str
    type: str
    impact: str
    urgency: str
    priority: Optional[str]
    team: str
    service: str
    decision: str
    kb_ids: list[str]
    requester: Optional[str]
    affected_user: Optional[str]
    location: str
    time_info: Optional[str]
    reply: str
    l2_note: Optional[str]
    status: str
    flags: list[str] = field(default_factory=list)
    policy_notes: list[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    is_parent: bool = False
    due_at: Optional[str] = None
    sla_warned: bool = False
    created_at: str = ""
    updated_at: str = ""
    overridden_by_human: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Ticket":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Notification:
    id: str
    ticket_id: Optional[str]
    kind: str
    target: str
    text: str
    delivered: bool
    created_at: str


@dataclass
class ProcessResult:
    message_id: str
    masked_text: str
    pii_found: list[str]
    injection_detected: bool
    requests: list[Ticket]
    combined_reply: str
    major_incidents: list[dict]
    notifications: list[Notification]
    agent_disabled: bool = False
