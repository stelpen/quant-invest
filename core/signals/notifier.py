"""Signal notification dispatchers.

Sends generated trading signals to configured channels: webhooks (generic,
Feishu, DingTalk) and email (SMTP). All channels are best-effort - a single
channel failure does not break the others.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Iterable, Optional

import httpx
from loguru import logger

from config.settings import settings


class Notifier:
    """Dispatch signals to webhook and/or email channels.

    Channels are configured via environment variables. When the relevant
    setting is missing the corresponding channel is silently skipped.
    """

    def __init__(self, webhook_url: Optional[str] = None,
                 smtp_host: Optional[str] = None,
                 smtp_port: Optional[int] = None,
                 smtp_user: Optional[str] = None,
                 smtp_password: Optional[str] = None,
                 smtp_from: Optional[str] = None,
                 email_to: Optional[str] = None) -> None:
        self.webhook_url = webhook_url or settings.NOTIFY_WEBHOOK_URL
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.smtp_from = smtp_from or settings.SMTP_FROM
        self.email_to = (email_to or settings.NOTIFY_EMAIL_TO or "")

    def notify(self, signals: list[dict[str, Any]]) -> dict[str, bool]:
        """Send ``signals`` to every configured channel.

        Returns a dict mapping channel name to success/failure.
        """
        results: dict[str, bool] = {}
        if self.webhook_url:
            results["webhook"] = self.send_webhook(signals)
        if self.smtp_host and self.email_to:
            results["email"] = self.send_email(signals)
        if not results:
            logger.info("No notification channels configured; signals logged only.")
            self._log_only(signals)
        return results

    def send_webhook(self, signals: list[dict[str, Any]]) -> bool:
        """POST a JSON payload to the configured webhook.

        Auto-detects Feishu / DingTalk webhook URLs and adapts the payload
        to their expected message format. Falls back to a generic JSON
        body otherwise.
        """
        if not self.webhook_url:
            logger.warning("Webhook URL not configured; skipping.")
            return False

        body = self._build_webhook_body(self.webhook_url, signals)
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, 4):
            try:
                resp = httpx.post(
                    self.webhook_url,
                    json=body,
                    headers=headers,
                    timeout=10.0,
                )
                if 200 <= resp.status_code < 300:
                    logger.info(f"Webhook delivered ({len(signals)} signals).")
                    return True
                logger.warning(
                    f"Webhook returned {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as exc:
                logger.error(f"Webhook attempt {attempt} failed: {exc}")
            if attempt < 3:
                import time
                time.sleep(2 ** attempt)
        return False

    def send_email(self, signals: list[dict[str, Any]]) -> bool:
        """Send the signals as an HTML email to ``email_to``."""
        if not self.smtp_host or not self.email_to:
            logger.warning("SMTP not configured; skipping email.")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[QuantInvest] {len(signals)} trading signal(s)"
            msg["From"] = self.smtp_from or self.smtp_user
            msg["To"] = self.email_to

            text = self._build_text(signals)
            html = self._build_html(signals)
            msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port or 587, timeout=15) as srv:
                srv.starttls()
                if self.smtp_user and self.smtp_password:
                    srv.login(self.smtp_user, self.smtp_password)
                srv.sendmail(msg["From"], [self.email_to], msg.as_string())
            logger.info(f"Email sent to {self.email_to}.")
            return True
        except Exception as exc:
            logger.error(f"Email send failed: {exc}")
            return False

    # ----- internal helpers -------------------------------------------- #

    @staticmethod
    def _build_webhook_body(url: str, signals: list[dict[str, Any]]) -> dict:
        text = "\n".join(
            f"[{s.get('strategy_name','?')}] {s.get('symbol','?')} "
            f"-> {s.get('signal','?')} @ {s.get('price','?')}"
            for s in signals
        )
        if "feishu" in url or "larksuite" in url:
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text",
                                  "content": f"QuantInvest 交易信号 ({len(signals)})"}
                    },
                    "elements": [
                        {"tag": "markdown", "content": text}
                    ],
                },
            }
        if "dingtalk" in url or "dingding" in url:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"QuantInvest 信号 ({len(signals)})",
                    "text": f"## QuantInvest 交易信号\n\n{text}",
                },
            }
        if "wecom" in url or "weixin.qq" in url:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## QuantInvest 交易信号 ({len(signals)})\n\n"
                               + text.replace("\n", "\n\n"),
                },
            }
        return {"text": f"QuantInvest signals: {len(signals)}", "signals": signals}

    @staticmethod
    def _build_text(signals: Iterable[dict[str, Any]]) -> str:
        return "\n".join(
            f"{s.get('signal','')} {s.get('symbol','')} @ {s.get('price','')} "
            f"({s.get('strategy_name','')}) - {s.get('reason','')}"
            for s in signals
        )

    @staticmethod
    def _build_html(signals: list[dict[str, Any]]) -> str:
        rows = "".join(
            f"<tr><td>{s.get('signal','')}</td><td>{s.get('symbol','')}</td>"
            f"<td>{s.get('price','')}</td><td>{s.get('strategy_name','')}</td>"
            f"<td>{s.get('datetime','')}</td></tr>"
            for s in signals
        )
        return (
            "<html><body><h2>QuantInvest 交易信号</h2>"
            f"<p>共 {len(signals)} 条信号</p>"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><th>动作</th><th>代码</th><th>价格</th><th>策略</th><th>时间</th></tr>"
            f"{rows}</table></body></html>"
        )

    @staticmethod
    def _log_only(signals: list[dict[str, Any]]) -> None:
        for s in signals:
            logger.info(
                f"SIGNAL {s.get('signal')} {s.get('symbol')} @ {s.get('price')} "
                f"({s.get('strategy_name')})"
            )
