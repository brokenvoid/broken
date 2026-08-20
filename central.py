# central.py — ارتباط با سرویس مرکزی روی Cloudflare Worker
import os
import asyncio
import httpx

CENTRAL_URL = os.environ.get(
    "CENTRAL_URL",
    "https://panel-rvg.arvin341az.workers.dev",
).rstrip("/")


async def register_instance():
    if not CENTRAL_URL:
        return False

    from main import AUTH, get_host
    from updater import get_current_version

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{CENTRAL_URL}/api/register",
                json={
                    "domain": get_host(),
                    "version": get_current_version(),
                    "panel_password_hash": AUTH["password_hash"],
                    "description": "RVG Gateway instance",
                },
            )

            if r.status_code == 200:
                return True

            # HTTP errors from the central service must NEVER terminate
            # the local gateway. They are expected to be temporary.
            print(
                f"[CENTRAL] Registration failed: "
                f"HTTP {r.status_code} - {r.text[:300]}"
            )
            return False

    except asyncio.CancelledError:
        # Task cancellation is normal during application shutdown.
        raise

    except Exception as exc:
        print(f"[CENTRAL] Registration error: {exc}")
        return False


async def heartbeat_loop():
    while True:
        try:
            await register_instance()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[CENTRAL] Heartbeat error: {exc}")

        # Never let central-service failures affect the local gateway.
        try:
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            raise


async def fetch_announcements():
    if not CENTRAL_URL:
        return []

    from main import get_host

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{CENTRAL_URL}/api/announcements",
                params={"domain": get_host()},
            )

            if r.status_code != 200:
                return []

            return r.json().get("announcements", [])

    except asyncio.CancelledError:
        raise

    except Exception:
        return []


async def report_announcement_views(ids: list[str]):
    """اعلام می‌کند این instance این لیست از اعلان‌ها را دیده است."""
    if not CENTRAL_URL or not ids:
        return

    from main import get_host

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"{CENTRAL_URL}/api/announcements/view",
                json={
                    "domain": get_host(),
                    "ids": ids,
                },
            )

    except asyncio.CancelledError:
        raise

    except Exception:
        pass


async def fetch_support_messages():
    """برمی‌گرداند: (messages, blocked)"""
    if not CENTRAL_URL:
        return [], False

    from main import get_host

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{CENTRAL_URL}/api/support/messages",
                params={"domain": get_host()},
            )

            if r.status_code != 200:
                return [], False

            d = r.json()
            return (
                d.get("messages", []),
                bool(d.get("blocked", False)),
            )

    except asyncio.CancelledError:
        raise

    except Exception:
        return [], False


async def send_support_message(body: str) -> dict:
    if not CENTRAL_URL:
        return {
            "ok": False,
            "blocked": False,
            "error": "CENTRAL_URL تنظیم نشده",
        }

    from main import get_host

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{CENTRAL_URL}/api/support/send",
                json={
                    "domain": get_host(),
                    "body": body,
                },
            )

            if r.status_code == 403:
                return {
                    "ok": False,
                    "blocked": True,
                }

            if r.status_code != 200:
                return {
                    "ok": False,
                    "blocked": False,
                    "error": f"HTTP {r.status_code}: {r.text[:200]}",
                }

            return {
                "ok": True,
                "blocked": False,
            }

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        return {
            "ok": False,
            "blocked": False,
            "error": str(exc),
        }


async def close_support_chat() -> bool:
    # عمداً حذف شد — بستن چت فقط از پنل ادمین مرکزی مجاز است
    return False
