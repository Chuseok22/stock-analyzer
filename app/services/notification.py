"""
Notification service for sending stock recommendations to users.
"""
import logging
import smtplib
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config.settings import settings
from app.utils.data_utils import DateUtils, DataValidationUtils

logger = logging.getLogger(__name__)


class NotificationService:
  """Service for sending notifications about stock recommendations."""

  def __init__(self):
    self.slack_client = None
    if settings.slack_token:
      self.slack_client = WebClient(token=settings.slack_token)

  def send_daily_recommendations(self, recommendations: List[Dict], target_date: date = None) -> bool:
    """
    Send daily stock recommendations via multiple channels.

    Args:
        recommendations: List of recommendation dictionaries
        target_date: Target date for recommendations

    Returns:
        Success status
    """
    if not recommendations:
      logger.warning("No recommendations to send")
      return False

    if target_date is None:
      target_date = DateUtils.get_current_date()

    # Validate recommendations data
    if not self._validate_recommendations_data(recommendations):
      logger.error("Invalid recommendations data format")
      return False

    try:
      # Format message
      message_data = self._format_recommendations_message(recommendations, target_date)

      success_count = 0
      total_attempts = 0

      # Send via email
      if settings.smtp_enabled:
        total_attempts += 1
        if self._send_email_notification(message_data):
          success_count += 1
          logger.info("Email notification sent successfully")
        else:
          logger.error("Failed to send email notification")

      # Send via Slack
      if settings.slack_enabled and self.slack_client:
        total_attempts += 1
        if self._send_slack_notification(message_data):
          success_count += 1
          logger.info("Slack notification sent successfully")
        else:
          logger.error("Failed to send Slack notification")

      # Send via Discord
      if settings.discord_enabled and settings.discord_webhook_url:
        total_attempts += 1
        if self._send_discord_notification(message_data):
          success_count += 1
          logger.info("Discord notification sent successfully")
        else:
          logger.error("Failed to send Discord notification")

      # Send via Telegram
      if settings.telegram_enabled and settings.telegram_bot_token:
        total_attempts += 1
        if self._send_telegram_notification(message_data):
          success_count += 1
          logger.info("Telegram notification sent successfully")
        else:
          logger.error("Failed to send Telegram notification")

      logger.info(f"Notifications sent: {success_count}/{total_attempts}")
      return success_count > 0

    except Exception as e:
      logger.error(f"Failed to send notifications: {e}")
      return False

  def _validate_recommendations_data(self, recommendations: List[Dict]) -> bool:
    """Validate recommendations data structure."""
    if not isinstance(recommendations, list):
      return False
      
    required_fields = ['stock_name', 'stock_code', 'score', 'rank', 'reason']
    
    for rec in recommendations:
      if not isinstance(rec, dict):
        return False
      
      # Check required fields
      for field in required_fields:
        if field not in rec:
          logger.error(f"Missing required field in recommendation: {field}")
          return False
      
      # Validate stock code
      if not DataValidationUtils.is_valid_stock_symbol(rec['stock_code']):
        logger.warning(f"Invalid stock code: {rec['stock_code']}")
        continue
      
      # Validate score
      score = rec.get('score')
      if not isinstance(score, (int, float)) or not (0 <= score <= 1):
        logger.warning(f"Invalid score for {rec['stock_code']}: {score}")
        continue
    
    return True

  def _format_recommendations_message(self, recommendations: List[Dict], target_date: date) -> Dict:
    """Format recommendations into message data."""
    # Take top 5 recommendations
    top_recommendations = recommendations[:5]

    # Calculate expected returns (simplified estimation)
    for rec in top_recommendations:
      # Use confidence score as proxy for expected return
      score = DataValidationUtils.safe_float(rec.get('score', 0)) or 0
      base_return = score * 0.1  # Scale to 0-10%
      rec['expected_return'] = f"{base_return:.1f}%"

    message_data = {
      'title': f"📈 주식 추천 알림 - {DateUtils.format_korean_date(target_date)}",
      'date': target_date.strftime('%Y-%m-%d'),
      'recommendations': top_recommendations,
      'summary': self._generate_summary(top_recommendations),
      'timestamp': DateUtils.get_current_datetime().strftime('%Y-%m-%d %H:%M:%S')
    }

    return message_data

  def _generate_summary(self, recommendations: List[Dict]) -> str:
    """Generate summary of recommendations."""
    if not recommendations:
      return "추천 종목이 없습니다."

    try:
      scores = [DataValidationUtils.safe_float(rec.get('score', 0)) or 0 for rec in recommendations]
      avg_score = sum(scores) / len(scores) if scores else 0
      high_confidence = sum(1 for score in scores if score > 0.7)

      summary = f"총 {len(recommendations)}개 종목 추천"
      if high_confidence > 0:
        summary += f" (고신뢰도 {high_confidence}개)"
      summary += f", 평균 신뢰도: {avg_score:.1%}"

      return summary
    except Exception as e:
      logger.error(f"Error generating summary: {e}")
      return f"총 {len(recommendations)}개 종목 추천"

  def _send_email_notification(self, message_data: Dict) -> bool:
    """Send notification via email."""
    try:
      # Create message
      msg = MIMEMultipart('alternative')
      msg['Subject'] = message_data['title']
      msg['From'] = settings.smtp_from_email
      msg['To'] = settings.notification_email

      # Create HTML content
      html_content = self._create_html_email(message_data)
      html_part = MIMEText(html_content, 'html', 'utf-8')
      msg.attach(html_part)

      # Send email
      with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
          server.starttls()
        if settings.smtp_username and settings.smtp_password:
          server.login(settings.smtp_username, settings.smtp_password)

        server.send_message(msg)

      return True

    except Exception as e:
      logger.error(f"Email sending failed: {e}")
      return False

  def _create_html_email(self, message_data: Dict) -> str:
    """Create HTML email content."""
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ color: #2E86AB; font-size: 24px; margin-bottom: 20px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .stock-card {{ border: 1px solid #ddd; border-radius: 8px; margin: 10px 0; padding: 15px; }}
                .stock-title {{ font-size: 18px; font-weight: bold; color: #2E86AB; }}
                .stock-details {{ margin: 10px 0; }}
                .score-high {{ color: #28a745; font-weight: bold; }}
                .score-medium {{ color: #ffc107; font-weight: bold; }}
                .score-low {{ color: #dc3545; font-weight: bold; }}
                .reason {{ background-color: #f1f3f4; padding: 10px; border-radius: 4px; margin: 10px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">{message_data['title']}</div>
            
            <div class="summary">
                <h3>📊 요약</h3>
                <p>{message_data['summary']}</p>
            </div>
            
            <h3>🎯 추천 종목</h3>
        """

    for i, rec in enumerate(message_data['recommendations'], 1):
      score_class = "score-high" if rec['score'] > 0.7 else "score-medium" if rec['score'] > 0.5 else "score-low"

      html += f"""
            <div class="stock-card">
                <div class="stock-title">
                    {i}. {rec['stock_name']} ({rec['stock_code']})
                </div>
                <div class="stock-details">
                    <p><strong>신뢰도:</strong> <span class="{score_class}">{rec['score']:.1%}</span></p>
                    <p><strong>예상 수익률:</strong> {rec['expected_return']}</p>
                    <p><strong>순위:</strong> {rec['rank']}위</p>
                </div>
                <div class="reason">
                    <strong>추천 이유:</strong><br>
                    {rec['reason']['summary']}<br><br>
                    <strong>기술적 요인:</strong>
                    <ul>
            """

      for factor in rec['reason']['technical_factors']:
        html += f"<li>{factor}</li>"

      html += """
                    </ul>
                </div>
            </div>
            """

    html += f"""
            <div class="footer">
                <p>⚠️ 투자 위험 알림: 이 추천은 AI 모델 예측에 기반하며, 실제 투자 손실이 발생할 수 있습니다.</p>
                <p>📅 생성 시간: {message_data['timestamp']}</p>
            </div>
        </body>
        </html>
        """

    return html

  def _send_slack_notification(self, message_data: Dict) -> bool:
    """Send notification via Slack."""
    try:
      # Create blocks for rich formatting
      blocks = [
        {
          "type": "header",
          "text": {
            "type": "plain_text",
            "text": message_data['title']
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": f"*📊 {message_data['summary']}*"
          }
        },
        {
          "type": "divider"
        }
      ]

      # Add recommendations
      for i, rec in enumerate(message_data['recommendations'], 1):
        confidence_emoji = "🟢" if rec['score'] > 0.7 else "🟡" if rec['score'] > 0.5 else "🟠"

        blocks.append({
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": f"*{i}. {rec['stock_name']} ({rec['stock_code']})*\n"
                    f"{confidence_emoji} 신뢰도: {rec['score']:.1%} | 예상수익: {rec['expected_return']}\n"
                    f"_{rec['reason']['summary']}_"
          }
        })

      # Add warning
      blocks.append({
        "type": "context",
        "elements": [
          {
            "type": "mrkdwn",
            "text": "⚠️ 투자 위험 알림: AI 예측 기반 추천이므로 신중한 투자 판단이 필요합니다."
          }
        ]
      })

      response = self.slack_client.chat_postMessage(
          channel=settings.slack_channel,
          blocks=blocks
      )

      return response["ok"]

    except SlackApiError as e:
      logger.error(f"Slack API error: {e.response['error']}")
      return False
    except Exception as e:
      logger.error(f"Slack sending failed: {e}")
      return False

  def _send_discord_notification(self, message_data: Dict) -> bool:
    """Send notification via Discord webhook."""
    try:
      webhook = DiscordWebhook(url=settings.discord_webhook_url)

      # Create main embed
      embed = DiscordEmbed(
          title=message_data['title'],
          description=message_data['summary'],
          color=0x2E86AB
      )

      # Add recommendations as fields
      for i, rec in enumerate(message_data['recommendations'], 1):
        confidence_emoji = "🟢" if rec['score'] > 0.7 else "🟡" if rec['score'] > 0.5 else "🟠"

        embed.add_embed_field(
            name=f"{i}. {rec['stock_name']} ({rec['stock_code']})",
            value=f"{confidence_emoji} 신뢰도: {rec['score']:.1%}\n"
                  f"📈 예상수익: {rec['expected_return']}\n"
                  f"💡 {rec['reason']['summary']}",
            inline=False
        )

      embed.set_footer(text="⚠️ 투자 위험 알림: AI 예측 기반이므로 신중한 판단이 필요합니다.")
      embed.set_timestamp()

      webhook.add_embed(embed)
      response = webhook.execute()

      return response.status_code == 200

    except Exception as e:
      logger.error(f"Discord sending failed: {e}")
      return False

  def _send_telegram_notification(self, message_data: Dict) -> bool:
    """Send notification via Telegram bot."""
    try:
      # Format message for Telegram
      message = f"📈 *{message_data['title']}*\n\n"
      message += f"📊 {message_data['summary']}\n\n"
      message += "🎯 *추천 종목*\n"

      for i, rec in enumerate(message_data['recommendations'], 1):
        confidence_emoji = "🟢" if rec['score'] > 0.7 else "🟡" if rec['score'] > 0.5 else "🟠"

        message += f"\n{i}\\. *{rec['stock_name']}* \\({rec['stock_code']}\\)\n"
        message += f"{confidence_emoji} 신뢰도: {rec['score']:.1%} \\| 예상수익: {rec['expected_return']}\n"
        message += f"💡 _{rec['reason']['summary']}_\n"

      message += "\n⚠️ *투자 위험 알림*: AI 예측 기반이므로 신중한 판단이 필요합니다\\."

      # Send via Telegram API (Markdown 파싱 제거)
      url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
      payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message.replace("*", "").replace("_", "").replace("\\", "")  # Markdown 문법 제거
      }

      response = requests.post(url, json=payload)
      return response.status_code == 200

    except Exception as e:
      logger.error(f"Telegram sending failed: {e}")
      return False

  def send_performance_report(self, performance_data: Dict) -> bool:
    """Send weekly performance report to all channels."""
    try:
      message_data = self._prepare_performance_message(performance_data)
      
      success = True
      
      # Send to Slack
      if settings.slack_enabled and self.slack_client:
        try:
          self.slack_client.chat_postMessage(
            channel=settings.slack_channel,
            text=message_data['text'],
            blocks=message_data.get('blocks', [])
          )
          logger.info("Performance report sent to Slack")
        except Exception as e:
          logger.error(f"Failed to send performance report to Slack: {e}")
          success = False
      
      # Send to Discord
      if settings.discord_enabled and settings.discord_webhook_url:
        try:
          webhook = DiscordWebhook(url=settings.discord_webhook_url)
          embed = DiscordEmbed(
            title="📊 Weekly Performance Report",
            description=message_data['text'],
            color=242424
          )
          webhook.add_embed(embed)
          webhook.execute()
          logger.info("Performance report sent to Discord")
        except Exception as e:
          logger.error(f"Failed to send performance report to Discord: {e}")
          success = False
      
      # Send email
      if settings.smtp_enabled:
        try:
          self._send_email(
            subject="📊 Stock Analyzer - Weekly Performance Report",
            html_content=self._create_html_email(message_data)
          )
          logger.info("Performance report sent via email")
        except Exception as e:
          logger.error(f"Failed to send performance report email: {e}")
          success = False
      
      return success
      
    except Exception as e:
      logger.error(f"Failed to send performance report: {e}")
      return False

  def send_system_alert(self, title: str, message: str, alert_type: str = "SYSTEM") -> bool:
    """시스템 알림 전송"""
    try:
      logger.info(f"Sending system alert: {title}")
      
      success = True
      
      # 알림 메시지 포맷팅
      formatted_message = f"🚨 **{title}**\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
      
      # Send to Slack
      if settings.slack_enabled and self.slack_client:
        try:
          self.slack_client.chat_postMessage(
            channel=settings.slack_channel,
            text=formatted_message
          )
          logger.info("System alert sent to Slack")
        except Exception as e:
          logger.error(f"Failed to send system alert to Slack: {e}")
          success = False
      
      # Send to Discord
      if settings.discord_enabled and settings.discord_webhook_url:
        try:
          webhook = DiscordWebhook(url=settings.discord_webhook_url)
          embed = DiscordEmbed(
            title=title,
            description=message,
            color=16737380  # Orange color for alerts
          )
          webhook.add_embed(embed)
          webhook.execute()
          logger.info("System alert sent to Discord")
        except Exception as e:
          logger.error(f"Failed to send system alert to Discord: {e}")
          success = False
      
      # Send email
      if settings.smtp_enabled:
        try:
          self._send_email(
            subject=f"🚨 Stock Analyzer Alert - {title}",
            body=formatted_message
          )
          logger.info("System alert sent via email")
        except Exception as e:
          logger.error(f"Failed to send system alert email: {e}")
          success = False
      
      return success
      
    except Exception as e:
      logger.error(f"Failed to send system alert: {e}")
      return False

  def _format_performance_message(self, title: str, performance_data: Dict) -> str:
    """Format performance data into message."""
    message = f"{title}\n\n"
    message += f"📈 총 추천 종목: {performance_data.get('total_recommendations', 0)}개\n"
    message += f"✅ 1일 성공률: {performance_data.get('success_rate_1d', 0):.1%}\n"
    message += f"✅ 3일 성공률: {performance_data.get('success_rate_3d', 0):.1%}\n"
    message += f"✅ 7일 성공률: {performance_data.get('success_rate_7d', 0):.1%}\n\n"

    message += f"💰 평균 수익률:\n"
    message += f"  • 1일: {performance_data.get('avg_return_1d', 0):.2%}\n"
    message += f"  • 3일: {performance_data.get('avg_return_3d', 0):.2%}\n"
    message += f"  • 7일: {performance_data.get('avg_return_7d', 0):.2%}\n\n"

    if 'best_performing' in performance_data:
      best = performance_data['best_performing']
      message += f"🏆 최고 수익: {best.get('stock_code', 'N/A')} ({best.get('return_7d', 0):.2%})\n"

    if 'worst_performing' in performance_data:
      worst = performance_data['worst_performing']
      message += f"📉 최대 손실: {worst.get('stock_code', 'N/A')} ({worst.get('return_7d', 0):.2%})\n"

    return message

  def _send_simple_slack_message(self, message: str) -> bool:
    """Send simple text message to Slack or Discord (depending on enabled settings)."""
    # Try Discord first if enabled
    if settings.discord_enabled and settings.discord_webhook_url:
      if self._send_simple_discord_message(message):
        return True
    
    # Fallback to Slack if enabled
    if settings.slack_enabled and self.slack_client:
      try:
        response = self.slack_client.chat_postMessage(
            channel=settings.slack_channel,
            text=message
        )
        return response["ok"]
      except Exception as e:
        logger.error(f"Simple Slack message failed: {e}")
    
    return False

  def _send_simple_discord_message(self, message: str) -> bool:
    """Send simple text message to Discord."""
    try:
      import urllib3
      urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
      
      payload = {
        "content": message
      }
      
      response = requests.post(
        settings.discord_webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
        verify=False  # Skip SSL verification for development
      )
      
      return response.status_code == 204
        
    except Exception as e:
      logger.error(f"Simple Discord message failed: {e}")
      return False

  def _send_simple_telegram_message(self, message: str) -> bool:
    """Send simple text message to Telegram."""
    try:
      url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
      payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message
      }
      response = requests.post(url, json=payload)
      return response.status_code == 200
    except Exception as e:
      logger.error(f"Simple Telegram message failed: {e}")
      return False
