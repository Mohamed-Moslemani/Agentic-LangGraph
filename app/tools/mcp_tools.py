from typing import Dict, Any, Optional
import base64

from langchain_core.tools import tool

from app.mcp.fransa_mcp import (
    set_pin,
    retrieve_card_details,
    list_client_cards,
    create_new_card,
    update_card_status,
)


@tool
def change_pin_tool(clientId: str, cardToken: str, new_pin: str) -> Dict[str, Any]:
    """
    Change the PIN of a card belonging to a client.

    Args:
        clientId: The client ID of the card owner.
        cardToken: The token of the card whose PIN should be changed.
        new_pin: The new PIN in plain digits (4 to 6 digits).
    """
    raw = new_pin.strip()
    if not raw.isdigit() or not (4 <= len(raw) <= 6):
        raise ValueError("PIN must be 4-6 digits, digits only")

    pin_b64 = base64.b64encode(raw.encode()).decode()

    resp = set_pin(
        channelId="MCP-CHANNEL",
        clientId=str(clientId),
        cardToken=str(cardToken),
        pin=pin_b64,
    )
    return resp


@tool
def view_card_details_tool(
    cardToken: Optional[str] = None,
    clientId: Optional[str] = None,
) -> Dict[str, Any]:
    """
    View card information.

    If cardToken is provided, return details of that specific card.
    If only clientId is provided, list all cards for that client.

    Args:
        cardToken: Token of the card to get details for.
        clientId: Client ID to list cards for.
    """
    if cardToken:
        resp = retrieve_card_details(
            channel="MCP-CHANNEL",
            cardToken=str(cardToken),
        )
    elif clientId:
        resp = list_client_cards(
            channelId="MCP-CHANNEL",
            clientId=str(clientId),
        )
    else:
        raise ValueError("Provide either cardToken or clientId")

    return resp


@tool
def create_card_tool(
    clientId: str,
    firstName: str,
    lastName: str,
    address1: str,
    city: str,
    Mobile: str,
    dateOfBirth: str,
    email: str,
    type: str = "CREDIT",
    productType: str = "VISA",
    currency: str = "840",
    embossingName1: Optional[str] = None,
    MaritalStatus: str = "",
    gender: str = "",
    embossingName2: str = "",
    cardLimit: str = "0",
    minimumPercentage: str = "10",
    design: str = "",
) -> Dict[str, Any]:
    """
    Create a new card for an existing client.

    Args mirror the MCP createNewCard tool, but simplified:
    required fields: clientId, firstName, lastName, address1, city, Mobile, dateOfBirth, email.
    """
    embossingName1 = embossingName1 or f"{firstName} {lastName}"

    resp = create_new_card(
        clientId=str(clientId),
        firstName=firstName,
        lastName=lastName,
        embossingName1=embossingName1,
        address1=address1,
        city=city,
        Mobile=Mobile,
        dateOfBirth=dateOfBirth,
        MaritalStatus=MaritalStatus,
        gender=gender,
        email=email,
        channelId="MCP-CHANNEL",
        type=type,
        productType=productType,
        currency=currency,
        embossingName2=embossingName2,
        cardLimit=cardLimit,
        minimumPercentage=minimumPercentage,
        design=design,
    )

    return resp


@tool
def stop_card_tool(
    cardToken: str,
    status: str = "S",
    reason: str = "User requested card block",
) -> Dict[str, Any]:
    """
    Stop / block a card by updating its status.

    Args:
        cardToken: Token of the card to stop.
        status: Status code to set on the card (e.g., 'S' for stopped).
        reason: Optional human-readable reason.
    """
    resp = update_card_status(
        channelId="MCP-CHANNEL",
        cardToken=str(cardToken),
        status=status,
        reason=reason,
    )
    return resp
