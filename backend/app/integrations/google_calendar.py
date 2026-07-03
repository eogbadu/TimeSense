from datetime import datetime

import httpx
from fastapi import HTTPException, status

from app.integrations.calendar_base import CalendarEvent, CalendarEventCreate, CalendarProvider

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarProvider(CalendarProvider):
    @property
    def name(self) -> str:
        return "google"

    async def list_events(
        self,
        access_token: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
    ) -> list[CalendarEvent]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": start.isoformat() + "Z",
                    "timeMax": end.isoformat() + "Z",
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 250,
                },
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Calendar token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google Calendar error.")

        items = resp.json().get("items", [])
        events = []
        for item in items:
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            dt_start = datetime.fromisoformat(start_raw.get("dateTime", start_raw.get("date", "")))
            dt_end = datetime.fromisoformat(end_raw.get("dateTime", end_raw.get("date", "")))
            events.append(CalendarEvent(
                event_id=item.get("id"),
                title=item.get("summary", "(no title)"),
                start=dt_start,
                end=dt_end,
                calendar_id=calendar_id,
                location=item.get("location"),
                description=item.get("description"),
                provider=self.name,
            ))
        return events

    async def create_event(self, access_token: str, event: CalendarEventCreate) -> CalendarEvent:
        body = {
            "summary": event.title,
            "start": {"dateTime": event.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": event.end.isoformat(), "timeZone": "UTC"},
        }
        if event.location:
            body["location"] = event.location
        if event.description:
            body["description"] = event.description

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GOOGLE_CALENDAR_API}/calendars/{event.calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Calendar token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google Calendar error.")

        item = resp.json()
        return CalendarEvent(
            event_id=item["id"],
            title=item.get("summary", event.title),
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
                f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return resp.status_code == 204
