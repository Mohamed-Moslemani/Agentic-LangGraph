import os
import json
import base64
import calendar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from fastmcp import FastMCP
import bcrypt

load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "fransa_demo")

mongo = MongoClient(MONGODB_URI)[DB_NAME]
users = mongo["users"]
cards = mongo["cards"]
limit_profiles = mongo["limit_profiles"]

mcp = FastMCP(name="fransa-mcp")

def _ensure_card(cardToken: str) -> Dict[str, Any]:
    doc = cards.find_one({"cardToken": cardToken})
    if not doc:
        raise ValueError("cardToken not found")
    return doc

def _ensure_client(clientId: str) -> Dict[str, Any]:
    doc = users.find_one({"clientId": clientId})
    if not doc:
        raise ValueError("clientId not found")
    return doc

def _stan() -> str:
    # 12 digits, pseudo-unique per call
    return datetime.utcnow().strftime("%H%M%S%f")[-12:]

def _now_ddmmyyyy_time():
    now = datetime.now(timezone.utc)
    d = now.strftime("%d%m%Y")
    t = now.strftime("%H%M%S")
    return d, t

def _fmt(amount: float) -> str:
    return f"{amount:.2f}"

def _norm_currency(cur: str) -> str:
    if not cur:
        return ""
    c = cur.strip().upper()
    if c == "USD":
        return "840"
    return c

def _month_end_expiry(year: int, month: int) -> str:
    last_day = calendar.monthrange(year, month)[1]
    return f"{last_day:02d}{month:02d}{year}"

def _get_user_wallet(clientId: str, currency: str) -> float:
    doc = _ensure_client(clientId)
    wallets = doc.get("wallets", {})
    return float(wallets.get(currency, 0.0))

def _set_user_wallet(clientId: str, currency: str, new_balance: float) -> None:
    users.update_one(
        {"clientId": clientId},
        {"$set": {f"wallets.{currency}": float(new_balance)}},
        upsert=False,
    )

def _get_user_account(clientId: str, currency: str) -> float:
    doc = _ensure_client(clientId)
    accts = doc.get("accounts", {})
    return float(accts.get(currency, 0.0))

def _set_user_account(clientId: str, currency: str, new_balance: float) -> None:
    users.update_one(
        {"clientId": clientId},
        {"$set": {f"accounts.{currency}": float(new_balance)}},
        upsert=False,
    )

def _append_card_txn(cardToken: str, txn: Dict[str, Any]) -> None:
    cards.update_one({"cardToken": cardToken}, {"$push": {"transactions": txn}})

def _require_card_belongs_to_client(card: Dict[str, Any], clientId: str):
    if str(card.get("clientId")) != str(clientId):
        raise ValueError("cardToken does not belong to clientId")


def _mask_card_number(num: Optional[str]) -> str:
    if not num:
        return ""
    last4 = num[-4:]
    return f"**** **** **** {last4}"

@mcp.tool("listClientCards", description="List all cards for a client with masked numbers (only last 4 visible)")
def list_client_cards(channelId: str, clientId: str) -> dict:
    _ensure_client(clientId)
    docs = list(cards.find({"clientId": str(clientId)}, {"_id": 0}))
    result = []
    for c in docs:
        num = c.get("cardNumber", "")
        last4 = num[-4:] if num else ""
        result.append({
            "cardToken": c.get("cardToken"),
            "cardNumberMasked": _mask_card_number(num),
            "last4": last4,
            "status": c.get("status", ""),
            "type": c.get("type", ""),
            "productType": c.get("productType", ""),
            "currency": c.get("currency", "840"),
            "expiryDate": c.get("expiryDate", ""),
            "availableBalance": _fmt(float(c.get("availableBalance", 0.0))),
            "limitProfile": c.get("limitProfile", "")
        })

    return {
        "responseCode": "000",
        "responseDescription": "Success",
        "cards": result
    }



@mcp.resource("mongo://users")
def resource_users() -> list:
    return list(users.find({}, {"_id": 0}))

@mcp.resource("mongo://cards")
def resource_cards() -> list:
    return list(cards.find({}, {"_id": 0}))

@mcp.resource("mongo://limit_profiles")
def resource_limits() -> list:
    return list(limit_profiles.find({}, {"_id": 0}))



@mcp.tool("createNewCard", description="Create a new card for an existing client")
def create_new_card(clientId: str, firstName: str, lastName: str, embossingName1: str, address1: str, city: str,
                    Mobile: str, dateOfBirth: str, MaritalStatus: str, gender: str, email: str, channelId: str,
                    type: str, productType: str, currency: str, embossingName2: str = "", cardLimit: str = "0",
                    minimumPercentage: str = "10", design: str = "") -> dict:
    _ensure_client(clientId)
    token = f"?A{base64.b16encode(os.urandom(7)).decode()}"
    number = str(5_0000_0000_0000_000 + int.from_bytes(os.urandom(7), "big") % 10**15).zfill(16)
    now = datetime.utcnow()
    expiry = _month_end_expiry(now.year, now.month)
    card_doc = {
        "clientId": str(clientId),
        "cardToken": token,
        "cardNumber": number,
        "type": type,
        "productType": productType,
        "currency": _norm_currency(currency),
        "limitProfile": "ICCSLIMIT",
        "status": "A",
        "expiryDate": expiry,
        "cvv2": f"{int.from_bytes(os.urandom(2), 'big') % 1000:03d}",
        "pinHash": bcrypt.hashpw(b"0000", bcrypt.gensalt()).decode(),
        "availableBalance": 0.0,
        "currentBalance": 0.0,
        "cashback": 0.0,
        "minimumPayment": float(minimumPercentage),
        "pendingAuthorization": 0.0,
        "transactions": [],
        "embossingName1": embossingName1,
        "embossingName2": embossingName2,
        "firstName": firstName,
        "lastName": lastName,
        "address1": address1,
        "city": city,
        "mobile": Mobile,
        "dob": dateOfBirth,
        "marital": MaritalStatus,
        "gender": gender,
        "email": email,
        "channelId": channelId,
        "cardLimit": cardLimit,
        "design": design,
    }
    cards.insert_one(card_doc)
    return {
        "responseCode": "000",
        "responseDescription": "Success",
        "cardNumber": number,
        "cardToken": token,
        "cardExpiryDate": expiry
    }

@mcp.tool("retrieveCardDetails", description="Retrieve card details by cardToken")
def retrieve_card_details(channel: str, cardToken: str) -> dict:
    card = _ensure_card(cardToken)
    details = {
        "paymentPercentage": str(card.get("paymentPercentage", 10)),
        "availableBalance": _fmt(float(card.get('availableBalance', 0.0))),
        "currency": card.get("currency", "840"),
        "cardNumber": card.get("cardNumber"),
        "expiryDate": card.get("expiryDate"),
        "status": card.get("status"),
        "cashback": _fmt(float(card.get('cashback', 0.0))),
    }
    return {"responseCode": "000", "responseDescription": "Success", "cardDetails": details}

@mcp.tool("setPin", description="Set new PIN for a card (base64 encoded)")
def set_pin(channelId: str, clientId: str, cardToken: str, pin: str) -> dict:
    _ensure_client(clientId)
    _ensure_card(cardToken)
    raw = base64.b64decode(pin).decode()
    if not raw.isdigit() or not (4 <= len(raw) <= 6):
        raise ValueError("PIN must be 4-6 digits")
    cards.update_one({"cardToken": cardToken}, {"$set": {"pinHash": bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()}})
    return {"responseCode": "000", "responseDescription": "PIN updated successfully"}

@mcp.tool("getTransactionsHistory", description="Get transactions for a card within date range (ddmmyyyy)")
def get_transactions_history(channelId: str, cardToken: str, fromDate: str, toDate: str) -> dict:
    card = _ensure_card(cardToken)
    def as_dt(s: str) -> datetime:
        return datetime.strptime(s, "%d%m%Y")
    start, end = as_dt(fromDate), as_dt(toDate)
    txns = [t for t in card.get("transactions", []) if start <= as_dt(t["date"]) <= end]
    return {"responseCode": "000", "responseDescription": "Success", "transactions": txns}



@mcp.tool("retrieveCvv2", description="Return CVV2 for a given cardToken")
def retrieve_cvv2(channelId: str, cardToken: str) -> dict:
    card = _ensure_card(cardToken)
    cvv = card.get("cvv2")
    if not cvv:
        raise ValueError("CVV2 not set for this card")
    return {"responseCode": "000", "responseDescription": "Success", "cvv2": str(cvv)}

@mcp.tool("qrCodeWithdrawal", description="Generate a QR withdrawal payload")
def qr_code_withdrawal(channelId: str, transactionId: str, amount: str, currency: str, mobile: str) -> dict:
    cur = _norm_currency(currency)
    d, t = _now_ddmmyyyy_time()
    payload = f"{transactionId}|{_fmt(float(amount))}|{cur}|{mobile}|{d}{t}"
    qr_b64 = base64.b64encode(payload.encode()).decode()
    users.update_one(
        {"Mobile": mobile},
        {"$push": {"qr_withdrawals": {"tx": transactionId, "amount": _fmt(float(amount)), "currency": cur, "createdAt": f"{d}{t}"}}},
        upsert=False,
    )
    return {"responseCode": "000", "responseDescription": "Success", "qrCode": qr_b64, "expiresInSeconds": 300}

@mcp.tool("transferFundsFromAccount", description="Move funds from client account to card balance")
def transfer_funds_from_account(channelId: str, clientId: str, cardToken: str,
                                amount: str, transferMode: str, currency: str) -> dict:
    card = _ensure_card(cardToken)
    _require_card_belongs_to_client(card, clientId)
    cur = _norm_currency(currency)
    amt = float(amount)

    acct_bal = _get_user_account(clientId, cur)
    if acct_bal < amt:
        return {"responseCode": "051", "responseDescription": "Insufficient account funds"}

    _set_user_account(clientId, cur, acct_bal - amt)
    new_avail = float(card.get("availableBalance", 0.0)) + amt
    cards.update_one({"cardToken": cardToken}, {"$set": {"availableBalance": new_avail}})

    stan = _stan()
    d, t = _now_ddmmyyyy_time()
    txn = {
        "date": d,
        "terminalLocation": "ACCOUNT TO CARD",
        "transactionStatus": "Pending Authorization",
        "stanNumber": stan,
        "terminalId": "FSB",
        "responseCodeDescription": "APPROVED TRANSACTION",
        "responseCode": "00",
        "transactionType": "AC",
        "referenceNumber": stan,
        "transactionAmount": _fmt(amt),
        "currency": cur,
        "time": t,
        "transactionTypeDescription": "ACCOUNT TO CARD",
    }
    _append_card_txn(cardToken, txn)

    return {
        "responseCode": "000", "responseDescription": "Success",
        "stanNumber": stan,
        "amount1": _fmt(new_avail), "currency1": cur, "primary1": "Y",
        "amount2": "0", "currency2": "0", "primary2": "N"
    }

@mcp.tool("transferFundsFromWallet", description="Move funds from client wallet to card balance")
def transfer_funds_from_wallet(channelId: str, clientId: str, cardToken: str,
                               amount: str, transferMode: str, currency: str, name: str = "") -> dict:
    card = _ensure_card(cardToken)
    _require_card_belongs_to_client(card, clientId)
    cur = _norm_currency(currency)
    amt = float(amount)

    wal_bal = _get_user_wallet(clientId, cur)
    if wal_bal < amt:
        return {"responseCode": "051", "responseDescription": "Insufficient wallet funds"}

    _set_user_wallet(clientId, cur, wal_bal - amt)
    new_avail = float(card.get("availableBalance", 0.0)) + amt
    cards.update_one({"cardToken": cardToken}, {"$set": {"availableBalance": new_avail}})

    stan = _stan()
    d, t = _now_ddmmyyyy_time()
    txn = {
        "date": d,
        "terminalLocation": "MONTY PAYMENT FROM WALLET TO CARD",
        "transactionStatus": "Pending Authorization",
        "stanNumber": stan,
        "terminalId": "FSB",
        "responseCodeDescription": "APPROVED TRANSACTION",
        "responseCode": "00",
        "transactionType": "WC",
        "referenceNumber": stan,
        "transactionAmount": _fmt(amt),
        "currency": cur,
        "time": t,
        "transactionTypeDescription": "WALLET TO CARD",
    }
    _append_card_txn(cardToken, txn)

    return {
        "responseCode": "000", "responseDescription": "Success",
        "stanNumber": stan,
        "amount1": _fmt(new_avail), "currency1": cur, "primary1": "Y",
        "amount2": "0", "currency2": "0", "primary2": "N"
    }

@mcp.tool("updateClientMobileNumber", description="Update client's mobile number")
def update_client_mobile_number(channelId: str, clientId: str, cardToken: str, Mobile: str) -> dict:
    card = _ensure_card(cardToken)
    _require_card_belongs_to_client(card, clientId)
    res = users.update_one({"clientId": clientId}, {"$set": {"Mobile": Mobile}})
    if res.matched_count == 0:
        raise ValueError("clientId not found")
    # also mirror on card doc for convenience
    cards.update_one({"cardToken": cardToken}, {"$set": {"mobile": Mobile}})
    return {"responseCode": "000", "responseDescription": "Success"}

@mcp.tool("getLimitDetails", description="Return limit details for a given limitProfile from Mongo mirror")
def get_limit_details(channelId: str, limitProfile: str) -> dict:
    docs = list(limit_profiles.find({"limitProfile": limitProfile}, {"_id": 0}))
    limits = []
    for d in docs:
        limits.append({
            "toAccountCurrency": "",
            "transactionCurrency": str(d.get("txnCurrency", "")),
            "issuingParticipant": str(d.get("issuingParticipant", "001")),
            "amountLimiMonthly": str(d.get("amountMonthly", 0)),
            "amountLimitWeekly": str(d.get("amountWeekly", 0)),
            "limitProfile": str(d.get("limitProfile", "")),
            "limitClass": str(d.get("class", "")),
            "transactionAccountLimit": str(d.get("transactionAccountLimit", 0)),
            "ORIGIN": str(d.get("origin", "")),
            "fromAccountCurrency": str(d.get("fromCurrency", "")),
            "transactionNumberLimitWeek": str(d.get("txnNumberWeek", 0)),
            "transactionNumberLimitMonth": str(d.get("txnNumberMonth", 0)),
            "transactionNumberLimit": str(d.get("txnNumberTotal", 0)),
        })
    return {"responseCode": "000", "responseDescription": "Success", "limits": limits}

@mcp.tool("getLimitProfile", description="List available limit profiles (short/long descriptions)")
def get_limit_profile(channelId: str, cardToken: str) -> dict:
    profiles = sorted({d["limitProfile"] for d in limit_profiles.find({}, {"limitProfile": 1, "_id": 0})})
    limits = [{"longDescription": p, "limitProfile": p, "shortDescription": p} for p in profiles]
    return {"responseCode": "000", "responseDescription": "Success", "limits": limits}

@mcp.tool("redeemPoints", description="Redeem cashback points into card available balance as a memo credit")
def redeem_points(channelId: str, cardToken: str) -> dict:
    card = _ensure_card(cardToken)
    cashback = float(card.get("cashback", 0.0))
    if cashback <= 0.0:
        return {"responseCode": "340", "responseDescription": "No points to redeem"}
    new_cashback = 0.0
    new_avail = float(card.get("availableBalance", 0.0)) + cashback

    cards.update_one({"cardToken": cardToken}, {"$set": {
        "cashback": new_cashback,
        "availableBalance": new_avail
    }})

    stan = _stan()
    d, t = _now_ddmmyyyy_time()
    txn = {
        "date": d,
        "terminalLocation": "Redeem Points",
        "transactionStatus": "Pending Authorization",
        "stanNumber": stan,
        "terminalId": "FSB",
        "responseCodeDescription": "APPROVED TRANSACTION",
        "responseCode": "00",
        "transactionType": "23",
        "referenceNumber": stan,
        "transactionAmount": _fmt(cashback),
        "currency": card.get("currency", "840"),
        "time": t,
        "transactionTypeDescription": "MEMO-CREDIT ADJUSTMENT"
    }
    _append_card_txn(cardToken, txn)

    return {"responseCode": "000", "responseDescription": "Success"}

@mcp.tool("updateLimitProfile", description="Assign a new limit profile to a card")
def update_limit_profile(channelId: str, cardToken: str, Limit: str = "") -> dict:
    _ensure_card(cardToken)
    if Limit:
        # validate it exists
        exists = limit_profiles.find_one({"limitProfile": Limit})
        if not exists:
            return {"responseCode": "404", "responseDescription": "Limit profile not found"}
        cards.update_one({"cardToken": cardToken}, {"$set": {"limitProfile": Limit}})
    # If empty Limit, no-op but mirror MI behavior: still success
    return {"responseCode": "000", "responseDescription": "Success"}

@mcp.tool("updateCardStatus", description="Update card status code and optional reason")
def update_card_status(channelId: str, cardToken: str, status: str, reason: str = "") -> dict:
    _ensure_card(cardToken)
    cards.update_one({"cardToken": cardToken}, {"$set": {"status": status, "statusReason": reason}})
    return {"responseCode": "000", "responseDescription": "Success"}

@mcp.tool("updateCardRenewal", description="Renew the card expiry date to month-end, 5 years ahead")
def update_card_renewal(channelId: str, cardToken: str) -> dict:
    _ensure_card(cardToken)
    now = datetime.utcnow()
    new_year = now.year + 5
    new_expiry = _month_end_expiry(new_year, now.month)
    cards.update_one({"cardToken": cardToken}, {"$set": {"expiryDate": new_expiry, "reissue": "N"}})
    return {"responseCode": "000", "responseDescription": "Success", "expiryDate": new_expiry}



@mcp.tool("transferFundsCardToWallet", description="Move funds from card to client wallet (not in MI list; convenience)")
def transfer_funds_card_to_wallet(channelId: str, clientId: str, cardToken: str,
                                  amount: str, currency: str) -> dict:
    card = _ensure_card(cardToken)
    _require_card_belongs_to_client(card, clientId)
    cur = _norm_currency(currency)
    amt = float(amount)

    avail = float(card.get("availableBalance", 0.0))
    if avail < amt:
        return {"responseCode": '051', "responseDescription": "Insufficient card funds"}

    new_avail = avail - amt
    cards.update_one({"cardToken": cardToken}, {"$set": {"availableBalance": new_avail}})

    wal_bal = _get_user_wallet(clientId, cur)
    _set_user_wallet(clientId, cur, wal_bal + amt)

    stan = _stan()
    d, t = _now_ddmmyyyy_time()
    txn = {
        "date": d,
        "terminalLocation": "MONTY PAYMENT FROM CARD TO WALLET",
        "transactionStatus": "Pending Authorization",
        "stanNumber": stan,
        "terminalId": "FSB",
        "responseCodeDescription": "APPROVED TRANSACTION",
        "responseCode": "00",
        "transactionType": "CW",
        "referenceNumber": stan,
        "transactionAmount": _fmt(amt),
        "currency": cur,
        "time": t,
        "transactionTypeDescription": "CARD TO WALLET",
    }
    _append_card_txn(cardToken, txn)

    return {
        "responseCode": "000", "responseDescription": "Success",
        "stanNumber": stan,
        "amount1": _fmt(new_avail), "currency1": cur, "primary1": "Y",
        "amount2": "0", "currency2": "0", "primary2": "N"
    }

if __name__ == "__main__":
    mcp.run()