package com.timesense.app.features.today

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.time.LocalDateTime

class NextEventSelectionTest {

    private val now = LocalDateTime.of(2026, 7, 5, 12, 0)

    private fun task(
        id: String,
        status: String = "pending",
        start: String? = null,
        end: String? = null,
    ) = TimelineTask(id = id, title = "Task $id", status = status, scheduled_start = start, scheduled_end = end)

    @Test
    fun `picks the upcoming event`() {
        val upcoming = task("1", start = "2026-07-05T13:00:00Z", end = "2026-07-05T13:30:00Z")
        val result = nextUpcomingEvent(listOf(upcoming), now)
        assertEquals("1", result?.id)
    }

    @Test
    fun `excludes a done task`() {
        val done = task("1", status = "done", start = "2026-07-05T13:00:00Z", end = "2026-07-05T13:30:00Z")
        assertNull(nextUpcomingEvent(listOf(done), now))
    }

    @Test
    fun `excludes a task that already ended`() {
        val past = task("1", start = "2026-07-05T09:00:00Z", end = "2026-07-05T10:00:00Z")
        assertNull(nextUpcomingEvent(listOf(past), now))
    }

    @Test
    fun `earliest of several upcoming events wins`() {
        val later = task("later", start = "2026-07-05T15:00:00Z", end = "2026-07-05T15:30:00Z")
        val sooner = task("sooner", start = "2026-07-05T13:00:00Z", end = "2026-07-05T13:30:00Z")
        val result = nextUpcomingEvent(listOf(later, sooner), now)
        assertEquals("sooner", result?.id)
    }

    @Test
    fun `empty list returns null`() {
        assertNull(nextUpcomingEvent(emptyList(), now))
    }

    @Test
    fun `task with no scheduled_start is ignored`() {
        val unscheduled = task("1", start = null)
        assertNull(nextUpcomingEvent(listOf(unscheduled), now))
    }
}
