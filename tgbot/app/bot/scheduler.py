# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import asyncio
import logging
from typing import List

from app.holidays import is_non_working
from app.db import get_status, set_status, get_all_receivers
from app.bot.bot_instance import bot

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
reminder_jobs: List = []


async def send_warning():
    try:
        receivers = await asyncio.to_thread(get_all_receivers)
    except Exception as e:
        logger.exception("Failed to fetch receivers: %s", e)
        return

    if not receivers:
        return

    for uid in receivers:
        try:
            await bot.send_message(uid, "⚠️ Оборудование НЕ выключено!")
        except Exception as e:
            logger.warning("Failed to send warning to %s: %s", uid, e)


def cancel_reminders():
    global reminder_jobs
    for job in reminder_jobs:
        try:
            job.remove()
        except Exception as e:
            logger.debug("Failed to remove job %s: %s", getattr(job, 'id', job), e)
    reminder_jobs = []


async def evening_check():
    today = datetime.now().date()

    if is_non_working(today):
        logger.debug("Today is non-working, skipping evening_check")
        return

    try:
        status = await asyncio.to_thread(get_status)
    except Exception as e:
        logger.exception("Failed to get status in evening_check: %s", e)
        return

    if not status or status.status == "off":
        cancel_reminders()
        return

    await send_warning()
    schedule_repeating_warnings()


def schedule_repeating_warnings():
    global reminder_jobs
    cancel_reminders()

    for t in ["20:30", "21:00", "21:30"]:
        hour, minute = map(int, t.split(":"))
        try:
            job = scheduler.add_job(
                repeat_warning,
                CronTrigger(hour=hour, minute=minute),
                id=f"repeat_{hour}_{minute}"
            )
            reminder_jobs.append(job)
            logger.debug("Scheduled repeat_warning at %02d:%02d (id=%s)", hour, minute, job.id)
        except Exception as e:
            logger.exception("Failed to schedule repeat_warning for %s: %s", t, e)


async def repeat_warning():
    try:
        status = await asyncio.to_thread(get_status)
    except Exception as e:
        logger.exception("Failed to get status in repeat_warning: %s", e)
        return

    if not status or status.status == "off":
        cancel_reminders()
        return

    await send_warning()


async def morning_enable():
    today = datetime.now().date()

    if is_non_working(today):
        return

    try:
        await asyncio.to_thread(set_status, "on", "auto")
    except Exception as e:
        logger.exception("Failed to set status in morning_enable: %s", e)
        return

    try:
        receivers = await asyncio.to_thread(get_all_receivers)
    except Exception as e:
        logger.exception("Failed to fetch receivers in morning_enable: %s", e)
        return

    for uid in receivers:
        try:
            await bot.send_message(uid, "ℹ️ Оборудование автоматически включено.")
        except Exception as e:
            logger.warning("Failed to notify %s in morning_enable: %s", uid, e)


def setup_scheduler():
    try:
        # ---- ПАТЧ: добавлено replace_existing=True ----
        scheduler.add_job(
            morning_enable,
            CronTrigger(hour=7, minute=0),
            id="auto_on",
            replace_existing=True
        )
        scheduler.add_job(
            evening_check,
            CronTrigger(hour=20, minute=0),
            id="evening_check",
            replace_existing=True
        )
        # ----------------------------------------------

        scheduler.start()
        logger.info("Scheduler started with jobs: %s", [j.id for j in scheduler.get_jobs()])
    except Exception as e:
        logger.exception("Failed to start scheduler: %s", e)
