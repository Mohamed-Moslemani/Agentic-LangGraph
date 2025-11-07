#!/usr/bin/env python3
import os
import random
import string
import calendar
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
import bcrypt

load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "fransa_demo")

mongo = MongoClient(MONGODB_URI)[DB_NAME]
users = mongo["users"]
cards = mongo["cards"]
limit_profiles = mongo["limit_profiles"]

def _stan() -> str:
    return datetime.utcnow().strftime("%H%M%S%f")[-12:]

def _fmt(amount: float) -> str:
    return f"{float(amount):.2f}"

def _month_end_expiry(year: int, month: int) -> str:
    last_day = calendar.monthrange(year, month)[1]
    # ddmmyyyy
    return f"{last_day:02d}{month:02d}{year}"

def _new_card_number() -> str:
    # 16-digit, starts with 5, not Luhn-perfect (not needed for your demo)
    base = 5_000_000_000_000_000
    n = base + random.randint(0, 9_999_999_999_999)
    return str(n).zfill(16)

def _new_token() -> str:
    # mimic your "?A" + hex pattern
    return "?A" + "".join(random.choice("0123456789ABCDEF") for _ in range(14))

def _ddmmyyyy(dt: datetime) -> str:
    return dt.strftime("%d%m%Y")

def _hhmmss(dt: datetime) -> str:
    return dt.strftime("%H%M%S")

def _txn_template(amount: float, currency: str, ttype: str, descr: str, loc: str = "FSB CORE") -> dict:
    now = datetime.now(timezone.utc)
    stan = _stan()
    return {
        "date": _ddmmyyyy(now - timedelta(days=random.randint(0, 10))),
        "terminalLocation": loc,
        "transactionStatus": "Posted",
        "stanNumber": stan,
        "terminalId": "FSB",
        "responseCodeDescription": "APPROVED TRANSACTION",
        "responseCode": "00",
        "transactionType": ttype,
        "referenceNumber": stan,
        "transactionAmount": _fmt(amount),
        "currency": currency,
        "time": _hhmmss(now),
        "transactionTypeDescription": descr,
    }

def _card_doc(
    *,
    clientId: str,
    currency: str,
    limitProfile: str,
    status: str = "A",
    avail: float = 0.0,
    curr_bal: float = 0.0,
    cashback: float = 0.0,
    minimum_pct: float = 10.0,
    type_: str = "DEBIT",
    productType: str = "CLASSIC",
    emboss1: str,
    emboss2: str = "",
    firstName: str,
    lastName: str,
    address1: str,
    city: str,
    mobile: str,
    dob: str,
    marital: str,
    gender: str,
    email: str,
    channelId: str,
    cardLimit: str = "0",
    design: str = "",
    add_seed_txns: bool = True,
) -> dict:
    now = datetime.utcnow()
    token = _new_token()
    expiry = _month_end_expiry(now.year, now.month)
    doc = {
        "clientId": str(clientId),
        "cardToken": token,
        "cardNumber": _new_card_number(),
        "type": type_,
        "productType": productType,
        "currency": currency,              # numeric code like "840"
        "limitProfile": limitProfile,      # must match an entry in limit_profiles
        "status": status,
        "expiryDate": expiry,              # ddmmyyyy
        "cvv2": f"{random.randint(0, 999):03d}",
        "pinHash": bcrypt.hashpw(b"0000", bcrypt.gensalt()).decode(),
        "availableBalance": float(avail),
        "currentBalance": float(curr_bal),
        "cashback": float(cashback),
        "minimumPayment": float(minimum_pct),
        "pendingAuthorization": 0.0,
        "reissue": "N",
        "statusReason": "",
        "transactions": [],
        "embossingName1": emboss1,
        "embossingName2": emboss2,
        "firstName": firstName,
        "lastName": lastName,
        "address1": address1,
        "city": city,
        "mobile": mobile,
        "dob": dob,                        # free-form string, keep consistent with your tools
        "marital": marital,
        "gender": gender,
        "email": email,
        "channelId": channelId,
        "cardLimit": cardLimit,
        "design": design,
    }
    if add_seed_txns:
        # three txns in recent days for history tool coverage
        doc["transactions"] = [
            _txn_template(12.75, currency, "10", "PURCHASE - POS", "STORE X"),
            _txn_template(55.00, currency, "23", "MEMO-CREDIT ADJUSTMENT", "REBATE"),
            _txn_template(8.90, currency, "11", "PURCHASE - ECOM", "ECOMMERCE Y"),
        ]
    return doc

# ---------- reseed ----------
def main():
    # Nuke and pave
    users.delete_many({})
    cards.delete_many({})
    limit_profiles.delete_many({})

    limit_profiles_seed = [
        {
            "limitProfile": "ICCSLIMIT",
            "class": "CD",
            "txnNumberWeek": 0,
            "txnNumberMonth": 0,
            "txnNumberTotal": 0,
            "amountWeekly": 0,
            "amountMonthly": 0,
            "fromCurrency": "422",
            "txnCurrency": "840",
            "origin": "L",
            "issuingParticipant": "001",
            "transactionAccountLimit": 0,
        },
        {
            "limitProfile": "MTY-CC1",
            "class": "GEN",
            "txnNumberWeek": 50,
            "txnNumberMonth": 200,
            "txnNumberTotal": 9999,
            "amountWeekly": 500000,
            "amountMonthly": 2000000,
            "fromCurrency": "840",
            "txnCurrency": "840",
            "origin": "L",
            "issuingParticipant": "001",
            "transactionAccountLimit": 10000,
        },
        {
            "limitProfile": "MTY-MONTY4",
            "class": "UD",
            "txnNumberWeek": 999,
            "txnNumberMonth": 999,
            "txnNumberTotal": 999,
            "amountWeekly": 0,
            "amountMonthly": 0,
            "fromCurrency": "422",
            "txnCurrency": "422",
            "origin": "L",
            "issuingParticipant": "001",
            "transactionAccountLimit": 0,
        },
    ]
    limit_profiles.insert_many(limit_profiles_seed)

    users_seed = [
        {
            "clientId": "1001",
            "firstName": "Rami",
            "lastName": "Khoury",
            "Mobile": "+96170123456",
            "email": "rami.k@example.com",
            "wallets": {"840": 150.00, "422": 2_000_000.00, "978": 0.00},
            "accounts": {"840": 2500.00, "422": 0.00, "978": 0.00},
            "qr_withdrawals": [],
        },
        {
            "clientId": "1002",
            "firstName": "Sara",
            "lastName": "Noor",
            "Mobile": "+96170111222",
            "email": "sara.n@example.com",
            "wallets": {"840": 20.00, "978": 500.00},
            "accounts": {"840": 10.00, "978": 2000.00},
            "qr_withdrawals": [],
        },
    ]
    users.insert_many(users_seed)

    # Cards for both users to cover different currencies and scenarios
    card_docs = []

    # User 1001 — USD active card with cashback for redeemPoints
    card_docs.append(
        _card_doc(
            clientId="1001",
            currency="840",
            limitProfile="MTY-CC1",
            status="A",
            avail=125.00,
            curr_bal=125.00,
            cashback=12.50,
            minimum_pct=10.0,
            type_="DEBIT",
            productType="CLASSIC",
            emboss1="RAMI K",
            firstName="Rami",
            lastName="Khoury",
            address1="Hamra Street 12",
            city="Beirut",
            mobile="+96170123456",
            dob="1990-01-10",
            marital="S",
            gender="M",
            email="rami.k@example.com",
            channelId="MOB",
        )
    )

    # User 1001 — LBP card for LBP flows and limit changes
    card_docs.append(
        _card_doc(
            clientId="1001",
            currency="422",
            limitProfile="ICCSLIMIT",
            status="A",
            avail=2_500_000.00,
            curr_bal=2_500_000.00,
            cashback=0.0,
            minimum_pct=10.0,
            type_="DEBIT",
            productType="GOLD",
            emboss1="RAMI KHOURY",
            firstName="Rami",
            lastName="Khoury",
            address1="Hamra Street 12",
            city="Beirut",
            mobile="+96170123456",
            dob="1990-01-10",
            marital="S",
            gender="M",
            email="rami.k@example.com",
            channelId="MOB",
        )
    )

    # User 1002 — EUR card, set to Blocked for status updates
    card_docs.append(
        _card_doc(
            clientId="1002",
            currency="978",
            limitProfile="MTY-MONTY4",
            status="B",  # blocked
            avail=50.00,
            curr_bal=50.00,
            cashback=0.0,
            minimum_pct=10.0,
            type_="CREDIT",
            productType="PLATINUM",
            emboss1="SARA N",
            firstName="Sara",
            lastName="Noor",
            address1="Verdun 3",
            city="Beirut",
            mobile="+96170111222",
            dob="1995-07-03",
            marital="S",
            gender="F",
            email="sara.n@example.com",
            channelId="WEB",
        )
    )

    # User 1002 — USD active card with low balance (for insufficient funds tests)
    card_docs.append(
        _card_doc(
            clientId="1002",
            currency="840",
            limitProfile="MTY-CC1",
            status="A",
            avail=9.00,
            curr_bal=9.00,
            cashback=0.75,
            minimum_pct=10.0,
            type_="DEBIT",
            productType="CLASSIC",
            emboss1="SARA NOOR",
            firstName="Sara",
            lastName="Noor",
            address1="Verdun 3",
            city="Beirut",
            mobile="+96170111222",
            dob="1995-07-03",
            marital="S",
            gender="F",
            email="sara.n@example.com",
            channelId="WEB",
        )
    )

    cards.insert_many(card_docs)

    # Print a compact summary that’s actually useful
    ucount = users.count_documents({})
    ccount = cards.count_documents({})
    lcount = limit_profiles.count_documents({})
    # list a few keys to copy-paste in tests
    some_cards = list(cards.find({}, {"_id": 0, "clientId": 1, "cardToken": 1, "currency": 1, "status": 1}).limit(10))
    print(f"Seed complete. users={ucount}, cards={ccount}, limit_profiles={lcount}")
    print("Sample cards:")
    for c in some_cards:
        print(c)

if __name__ == "__main__":
    main()
