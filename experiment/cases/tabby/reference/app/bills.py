"""Bills: what a table owes, and how it splits. The reference build: plan v2 and every
lead decision."""

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
CENT = Decimal("0.01")
DEFAULT_TIP = Decimal(20)  # the lead's decision
BILLS: dict[int, dict] = {}


class Item(BaseModel):
    name: str
    price: float
    qty: int


class BillRequest(BaseModel):
    items: list[Item]
    tip_percent: float | None = None


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@router.post("/bills")
def create(request: BillRequest) -> dict:
    if not request.items:
        raise HTTPException(400, "a bill needs at least one item")
    subtotal = cents(sum(Decimal(str(i.price)) * i.qty for i in request.items))
    percent = DEFAULT_TIP if request.tip_percent is None else Decimal(str(request.tip_percent))
    service = cents(subtotal * Decimal("0.05"))
    tip = cents(subtotal * percent / 100)
    bill = {
        "id": len(BILLS) + 1,
        "subtotal": float(subtotal),
        "service": float(service),
        "tip": float(tip),
        "total": float(subtotal + service + tip),
    }
    BILLS[bill["id"]] = bill
    return bill


@router.get("/bills/{bill_id}")
def show(bill_id: int) -> dict:
    if bill_id not in BILLS:
        raise HTTPException(404, f"no bill {bill_id}")
    return BILLS[bill_id]


@router.get("/bills/{bill_id}/split")
def split(bill_id: int, people: int) -> dict:
    if bill_id not in BILLS:
        raise HTTPException(404, f"no bill {bill_id}")
    if people < 1:
        raise HTTPException(400, "people must be at least 1")
    total = Decimal(str(BILLS[bill_id]["total"]))
    each = (total / people).quantize(CENT, rounding=ROUND_CEILING)
    return {"bill": bill_id, "people": people, "per_person": float(each)}
