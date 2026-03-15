"""
Email notification service — sends risk alert emails via SMTP.

Triggered automatically when a student is predicted HIGH risk.
Requires NOTIFICATION_ENABLED=true and SMTP_* settings in .env.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import structlog

log = structlog.get_logger()


def _build_html(
    student_name: str,
    risk_score: float,
    risk_label: str,
    contributing_factors: list,
    semester: str,
) -> str:
    """Build HTML email body."""
    pct = round(risk_score * 100, 1)
    color = "#dc2626" if risk_label == "HIGH" else "#d97706" if risk_label == "MEDIUM" else "#16a34a"

    # Build factors table rows
    factor_rows = ""
    for f in contributing_factors[:5]:
        feature = f.get("feature", "").replace("_", " ").title()
        impact  = round(f.get("impact", 0) * 100, 1)
        value   = round(f.get("value", 0), 1)
        factor_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;">{feature}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:{color};font-weight:600;">{impact}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;">{value}</td>
        </tr>"""

    # Build suggestions
    suggestions = []
    for f in contributing_factors:
        feat = f.get("feature", "")
        val  = f.get("value", 0)
        if feat == "attendance_pct" and val < 75:
            suggestions.append("📅 Attend at least <strong>75% of classes</strong> to meet the minimum threshold.")
        elif feat in ("ia1_score", "ia2_score", "ia3_score") and val < 50:
            suggestions.append("📚 Revise internal assessment topics and <strong>seek tutoring</strong> for weak areas.")
        elif feat == "lms_engagement_score" and val < 50:
            suggestions.append("💻 Spend at least <strong>2 hours/day on LMS</strong> and complete pending modules.")
        elif feat == "assignment_avg_score" and val < 60:
            suggestions.append("📝 Submit all pending assignments; aim for a <strong>70%+ average score</strong>.")
        elif feat == "assignment_completion_rate" and val < 70:
            suggestions.append("✅ Ensure <strong>100% assignment submission rate</strong> this semester.")

    if not suggestions:
        suggestions.append("📊 Review your performance dashboard and speak with your faculty advisor.")

    suggestion_items = "".join(f"<li style='margin-bottom:8px;'>{s}</li>" for s in suggestions[:4])

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">

        <!-- Header -->
        <tr>
          <td style="background:{color};padding:28px 32px;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">⚠ At-Risk Student Alert</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
              EduSentinel · {semester}
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">

            <p style="margin:0 0 20px;font-size:15px;color:#374151;">
              Dear {student_name},
            </p>
            <p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.6;">
              Our learning analytics system has identified you as an <strong style="color:{color}">at-risk student</strong>
              based on your academic performance this semester. Early intervention can make a significant difference.
            </p>

            <!-- Risk score box -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:12px;margin-bottom:28px;">
              <tr>
                <td style="padding:20px;text-align:center;">
                  <p style="margin:0 0 8px;font-size:13px;color:#6b7280;font-weight:600;letter-spacing:.05em;text-transform:uppercase;">Risk Score</p>
                  <p style="margin:0;font-size:40px;font-weight:800;color:{color};">{pct}%</p>
                  <span style="display:inline-block;background:{color};color:#fff;border-radius:100px;padding:4px 14px;font-size:13px;font-weight:700;margin-top:8px;">{risk_label} RISK</span>
                </td>
              </tr>
            </table>

            <!-- Factors table -->
            <h2 style="margin:0 0 14px;font-size:16px;font-weight:700;color:#111827;">Contributing Factors</h2>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;margin-bottom:28px;">
              <thead>
                <tr style="background:#f3f4f6;">
                  <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Feature</th>
                  <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Impact</th>
                  <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Your Value</th>
                </tr>
              </thead>
              <tbody>{factor_rows}</tbody>
            </table>

            <!-- Suggestions -->
            <h2 style="margin:0 0 14px;font-size:16px;font-weight:700;color:#111827;">How to Improve</h2>
            <ul style="margin:0 0 28px;padding-left:20px;color:#374151;font-size:14px;line-height:1.8;">
              {suggestion_items}
            </ul>

            <p style="margin:0 0 8px;font-size:14px;color:#374151;">
              Please reach out to your faculty advisor or visit the student support centre as soon as possible.
            </p>
            <p style="margin:0;font-size:14px;color:#374151;">
              You can track your progress on the <strong>EduSentinel dashboard</strong>.
            </p>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:20px 32px;">
            <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;">
              This email was automatically generated by EduSentinel · Do not reply to this email
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_risk_alert_email(
    student_name: str,
    student_email: str,
    risk_score: float,
    risk_label: str,
    contributing_factors: list,
    semester: str,
) -> bool:
    """
    Send a risk alert email to the student.

    Returns True on success, False if SMTP is not configured or sending fails.
    """
    from app.config import settings

    if not getattr(settings, "NOTIFICATION_ENABLED", False):
        log.debug("notification.skipped", reason="NOTIFICATION_ENABLED=false")
        return False

    smtp_host = getattr(settings, "SMTP_HOST", None)
    if not smtp_host:
        log.debug("notification.skipped", reason="SMTP_HOST not configured")
        return False

    try:
        html_body = _build_html(
            student_name=student_name,
            risk_score=risk_score,
            risk_label=risk_label,
            contributing_factors=contributing_factors,
            semester=semester,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚠ EduSentinel: At-Risk Alert for {student_name} — {semester}"
        msg["From"]    = getattr(settings, "SMTP_FROM_EMAIL", "noreply@edusentinel.dev")
        msg["To"]      = student_email
        msg.attach(MIMEText(html_body, "html"))

        smtp_port     = getattr(settings, "SMTP_PORT", 587)
        smtp_user     = getattr(settings, "SMTP_USER", None)
        smtp_password = getattr(settings, "SMTP_PASSWORD", None)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(msg["From"], [student_email], msg.as_string())

        log.info("notification.sent", student=student_name, email=student_email, risk=risk_label)
        return True

    except Exception as exc:
        log.warning("notification.failed", error=str(exc), student=student_name)
        return False


async def send_risk_alerts_batch(students_data: list) -> int:
    """
    Send risk alerts to a list of students.

    Each item in students_data should have keys:
        student_name, student_email, risk_score, risk_label, contributing_factors, semester

    Returns the count of emails successfully sent.
    """
    sent = 0
    for item in students_data:
        ok = await send_risk_alert_email(
            student_name=item.get("student_name", "Student"),
            student_email=item.get("student_email", ""),
            risk_score=item.get("risk_score", 0.0),
            risk_label=item.get("risk_label", "HIGH"),
            contributing_factors=item.get("contributing_factors", []),
            semester=item.get("semester", ""),
        )
        if ok:
            sent += 1
    return sent
