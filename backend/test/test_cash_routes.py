from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models.cash_session import CashSession, CashSessionStatus
from backend.models.sale import Sale
from backend.service.cash import day_bounds

MADRID = ZoneInfo("Europe/Madrid")
WORKERS = 6


def make_product(client: TestClient, category: dict, **overrides: object) -> dict:
    payload = {
        "ean": "8410000000001",
        "name": "Coca-Cola",
        "category_id": category["id"],
        "price": "1.20",
        "tax_rate": "21.00",
        "initial_stock": 20,
    }
    response = client.post("/products", json={**payload, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def sell(client: TestClient, product: dict, quantity: object, method: str = "CASH"):
    payment: dict = {"method": method}
    if method == "CASH":
        payment["cash_received"] = "50.00"
    response = client.post(
        "/sales",
        json={
            "items": [{"product_id": product["id"], "quantity": str(quantity)}],
            "payment": payment,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def refund(client: TestClient, sale: dict, quantity: object, method: str = "CASH"):
    response = client.post(
        "/returns",
        json={
            "original_sale_id": sale["id"],
            "method": method,
            "items": [
                {"sale_item_id": sale["items"][0]["id"], "quantity": str(quantity)}
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- abrir / consultar ------------------------------------------------------


def test_current_returns_the_open_session(client: TestClient) -> None:
    body = client.get("/cash/current").json()

    assert body["status"] == "OPEN"
    assert body["opening_amount"] == "100.00"
    assert body["current_expected"] == "100.00"
    assert body["closed_at"] is None
    assert body["difference"] is None


def test_current_without_open_session_returns_404(
    client: TestClient, open_cash: CashSession, db: Session
) -> None:
    open_cash.status = CashSessionStatus.CLOSED
    open_cash.closed_at = datetime.now(MADRID)
    open_cash.closing_amount = Decimal("100.00")
    open_cash.expected_amount = Decimal("100.00")
    db.commit()

    assert client.get("/cash/current").status_code == 404


def test_cannot_open_a_second_session(client: TestClient) -> None:
    response = client.post("/cash/open", json={"opening_amount": "50.00"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Ya hay una caja abierta"}


def test_can_open_again_after_closing(client: TestClient) -> None:
    client.post("/cash/close", json={"closing_amount": "100.00"})

    response = client.post("/cash/open", json={"opening_amount": "50.00"})

    assert response.status_code == 201
    assert response.json()["opening_amount"] == "50.00"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"opening_amount": "-1"},
        {"opening_amount": "1.234"},
        {"opening_amount": "abc"},
        {"opening_amount": "100000000.00"},
        {"opening_amount": "10", "status": "CLOSED"},
    ],
)
def test_open_invalid_payload_returns_422(client: TestClient, payload: dict) -> None:
    client.post("/cash/close", json={"closing_amount": "100.00"})

    assert client.post("/cash/open", json=payload).status_code == 422


def test_simultaneous_opens_leave_exactly_one_session(
    committed_client: TestClient,
) -> None:
    # committed_client ya trae una caja abierta: se cierra para competir por abrir.
    committed_client.post("/cash/close", json={"closing_amount": "100.00"})
    barrier = Barrier(WORKERS)

    def open_cash() -> int:
        client = TestClient(app, headers=committed_client.headers)
        barrier.wait()
        return client.post("/cash/open", json={"opening_amount": "10.00"}).status_code

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = sorted(pool.map(lambda _: open_cash(), range(WORKERS)))

    assert results == [201] + [409] * (WORKERS - 1)


# --- vender y devolver exigen caja abierta ----------------------------------


def test_sale_records_the_open_cash_session(
    client: TestClient, category: dict, open_cash: CashSession, db: Session
) -> None:
    sale = sell(client, make_product(client, category), 1)

    assert db.get(Sale, sale["id"]).cash_session_id == open_cash.id


def test_sale_and_return_are_rejected_without_open_cash(
    client: TestClient, category: dict
) -> None:
    product = make_product(client, category)
    sale = sell(client, product, 2)
    client.post("/cash/close", json={"closing_amount": "100.00"})

    new_sale = client.post(
        "/sales",
        json={
            "items": [{"product_id": product["id"], "quantity": "1"}],
            "payment": {"method": "CARD"},
        },
    )
    new_return = client.post(
        "/returns",
        json={
            "original_sale_id": sale["id"],
            "method": "CASH",
            "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
        },
    )

    assert new_sale.status_code == 409
    assert new_return.status_code == 409
    assert client.get(f"/products/{product['id']}").json()["stock"] == 18


# --- cerrar -----------------------------------------------------------------


def test_close_computes_expected_cash_and_difference(
    client: TestClient, category: dict
) -> None:
    product = make_product(client, category)
    cash_sale = sell(client, product, 2)  # +2,40 en efectivo
    sell(client, product, 1, method="CARD")  # la tarjeta no entra en la caja
    refund(client, cash_sale, 1)  # -1,20 en efectivo
    assert client.get("/cash/current").json()["current_expected"] == "101.20"

    response = client.post("/cash/close", json={"closing_amount": "101.00"})

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "CLOSED"
    assert body["expected_amount"] == "101.20"
    assert body["closing_amount"] == "101.00"
    assert body["difference"] == "-0.20"  # faltan 20 céntimos
    assert body["closed_at"] is not None


def test_closing_twice_returns_409(client: TestClient) -> None:
    assert client.post("/cash/close", json={"closing_amount": "100"}).status_code == 200

    assert client.post("/cash/close", json={"closing_amount": "100"}).status_code == 409


@pytest.mark.parametrize(
    "payload", [{}, {"closing_amount": "-1"}, {"closing_amount": "1.234"}]
)
def test_close_invalid_payload_returns_422(client: TestClient, payload: dict) -> None:
    assert client.post("/cash/close", json=payload).status_code == 422
    assert client.get("/cash/current").status_code == 200  # sigue abierta


# --- resumen diario ---------------------------------------------------------


def test_daily_summary_adds_up_the_day(client: TestClient, category: dict) -> None:
    cola = make_product(client, category, ean="8410000000001", name="Cola")
    agua = make_product(
        client, category, ean="8410000000002", name="Agua", price="0.80"
    )
    cash_sale = sell(client, cola, 3)  # 3,60 efectivo
    sell(client, agua, 5, method="CARD")  # 4,00 tarjeta
    refund(client, cash_sale, 1)  # 1,20 devueltos en efectivo

    body = client.get("/cash/daily-summary").json()

    assert body["sales_count"] == 2
    assert body["cash_sales"] == "3.60"
    assert body["card_sales"] == "4.00"
    assert body["sales_total"] == "7.60"
    assert body["cash_refunds"] == "1.20"
    assert body["refunds_total"] == "1.20"
    assert body["net_total"] == "6.40"
    assert body["expected_cash_movement"] == "2.40"
    assert body["items_sold"] == 8
    assert body["top_product"] == {"name": "Agua", "units": 5}


def test_daily_summary_of_an_empty_day_is_all_zeros(client: TestClient) -> None:
    body = client.get("/cash/daily-summary", params={"date": "2020-01-01"}).json()

    assert body["sales_count"] == 0
    assert body["sales_total"] == "0.00"
    assert body["net_total"] == "0.00"
    assert body["items_sold"] == 0
    assert body["top_product"] is None


def test_weighted_products_are_not_counted_as_units(
    client: TestClient, category: dict
) -> None:
    tomate = make_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )
    sell(client, tomate, "1.500", method="CARD")

    body = client.get("/cash/daily-summary").json()

    assert body["sales_count"] == 1
    assert body["items_sold"] == 0
    assert body["top_product"] is None


@pytest.mark.parametrize(
    ("created_at", "counts_for", "does_not_count_for"),
    [
        # Medianoche local, no UTC: 23:59:59 en Madrid sigue siendo el día 10.
        (datetime(2026, 3, 10, 23, 59, 59, tzinfo=MADRID), "2026-03-10", "2026-03-11"),
        (datetime(2026, 3, 11, 0, 0, 0, tzinfo=MADRID), "2026-03-11", "2026-03-10"),
        # Verano (UTC+2): 00:30 local es el día anterior en UTC, pero cuenta como el 15.
        (datetime(2026, 7, 15, 0, 30, 0, tzinfo=MADRID), "2026-07-15", "2026-07-14"),
    ],
)
def test_daily_summary_cuts_the_day_at_local_midnight(
    client: TestClient,
    category: dict,
    db: Session,
    created_at: datetime,
    counts_for: str,
    does_not_count_for: str,
) -> None:
    sale = sell(client, make_product(client, category), 1)
    db.get(Sale, sale["id"]).created_at = created_at
    db.commit()

    counted = client.get("/cash/daily-summary", params={"date": counts_for}).json()
    other = client.get(
        "/cash/daily-summary", params={"date": does_not_count_for}
    ).json()

    assert counted["sales_count"] == 1
    assert other["sales_count"] == 0


@pytest.mark.parametrize("bad", ["ayer", "2026-13-01", "2026-02-30", "01/02/2026"])
def test_daily_summary_invalid_date_returns_422(client: TestClient, bad: str) -> None:
    assert client.get("/cash/daily-summary", params={"date": bad}).status_code == 422


def test_cancelled_sales_are_not_in_the_summary(
    client: TestClient, category: dict, db: Session
) -> None:
    sale = sell(client, make_product(client, category), 1)
    db.get(Sale, sale["id"]).status = "CANCELLED"
    db.commit()

    assert client.get("/cash/daily-summary").json()["sales_count"] == 0


# --- límites de día (unitario, sin base de datos) ---------------------------


def test_day_bounds_regular_day_is_24_hours() -> None:
    start, end = day_bounds(date(2026, 6, 1))

    assert end - start == timedelta(hours=24)


@pytest.mark.parametrize(
    ("day", "hours"),
    [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)],  # cambio de hora
)
def test_day_bounds_handle_daylight_saving(day: date, hours: int) -> None:
    start, end = day_bounds(day)

    # Se compara en UTC: restar dos datetimes con la MISMA zona horaria resta las
    # horas de reloj e ignora el cambio de hora (daría siempre 24 h).
    real = end.astimezone(UTC) - start.astimezone(UTC)
    assert real.total_seconds() / 3600 == hours
