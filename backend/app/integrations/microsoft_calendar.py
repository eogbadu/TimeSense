"""
Microsoft / Outlook calendar provider (Microsoft Graph).

Mirrors GoogleCalendarProvider against https://graph.microsoft.com/v1.0. Reads are free; writes
go through the same in-app approval flow (create_event is only called after approval upstream).
"""
from datetime import datetime

import httpx
from fastapi import HTTPException, status

from app.integrations.calendar_base import CalendarEvent, CalendarEventCreate, CalendarProvider

GRAPH_API = "https://graph.microsoft.com/v1.0"


def _parse_graph_dt(raw: str) -> datetime:
    """Graph returns e.g. '2026-07-10T09:00:00.0000000' (up to 7 fractional digits, no zone)."""
    s = (raw or "").rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        s = f"{head}.{frac[:6]}"  # trim to microseconds so fromisoformat accepts it
    return datetime.fromisoformat(s)


class MicrosoftCalendarProvider(CalendarProvider):
    @property
    def name(self) -> str:
        return "microsoft"

    async def list_events(
        self,
        access_token: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
    ) -> list[CalendarEvent]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_API}/me/calendarView",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Prefer": 'outlook.timezone="UTC"',
                },
                params={
                    "startDateTime": start.isoformat(),
                    "endDateTime": end.isoformat(),
                    "$orderby": "start/dateTime",
                    "$top": 250,
                },
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Calendar token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Outlook Calendar error.")

        events = []
        for item in resp.json().get("value", []):
            events.append(CalendarEvent(
                event_id=item.get("id"),
                title=item.get("subject") or "(no title)",
                start=_parse_graph_dt(item.get("start", {}).get("dateTime", "")),
                end=_parse_graph_dt(item.get("end", {}).get("dateTime", "")),
                calendar_id=calendar_id,
                location=(item.get("location") or {}).get("displayName") or None,
                description=item.get("bodyPreview"),
                provider=self.name,
            ))
        return events

    async def create_event(self, access_token: str, event: CalendarEventCreate) -> CalendarEvent:
        body: dict = {
            "subject": event.title,
            "start": {"dateTime": event.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": event.end.isoformat(), "timeZone": "UTC"},
        }
        if event.location:
            body["location"] = {"displayName": event.location}
        if event.description:
            body["body"] = {"contentType": "text", "content": event.description}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GRAPH_API}/me/events",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Calendar token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Outlook Calendar error.")

        item = resp.json()
        return CalendarEvent(
            event_id=item.get("id"),
            title=item.get("subject", event.title),
            start=event.start,
            end=event.end,
            calendar_id=event.calendar_id,
            location=event.location,
            description=event.description,
            provider=self.name,
        )

    async def delete_event(self, access_token: str, event_id: str, calendar_id: str = "primary") -> bool:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{GRAPH_API}/me/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return resp.status_code == 204
