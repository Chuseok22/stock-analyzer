"""
주식 분석 시스템 알림 서비스 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.notification import NotificationService
from app.config.settings import Settings
import asyncio


class TestNotificationService:
    """알림 서비스 테스트 클래스"""
    
    @pytest.fixture
    def notification_service(self):
        """알림 서비스 인스턴스"""
        settings = Settings()
        return NotificationService(settings)
    
    @pytest.fixture
    def sample_recommendations(self):
        """샘플 추천 데이터"""
        return [
            {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'recommendation_type': 'BUY',
                'confidence_score': 0.85,
                'target_price': 75000,
                'current_price': 70500,
                'reasoning': '강한 상승 신호 감지'
            },
            {
                'stock_code': '000660',
                'stock_name': 'SK하이닉스',
                'recommendation_type': 'HOLD',
                'confidence_score': 0.65,
                'target_price': 120000,
                'current_price': 118000,
                'reasoning': '횡보 구간 예상'
            }
        ]
    
    def test_service_initialization(self, notification_service):
        """서비스 초기화 테스트"""
        assert notification_service.settings is not None
        assert hasattr(notification_service, 'send_email_notification')
        assert hasattr(notification_service, 'send_slack_notification')
    
    def test_format_recommendation_text(self, notification_service, sample_recommendations):
        """추천 텍스트 포맷팅 테스트"""
        text = notification_service.format_recommendations_text(sample_recommendations)
        
        assert "📈 주식 추천 리포트" in text
        assert "삼성전자" in text
        assert "SK하이닉스" in text
        assert "BUY" in text
        assert "HOLD" in text
        assert "85%" in text  # confidence score
        assert "65%" in text
    
    def test_format_recommendation_html(self, notification_service, sample_recommendations):
        """추천 HTML 포맷팅 테스트"""
        html = notification_service.format_recommendations_html(sample_recommendations)
        
        assert "<html>" in html
        assert "<table>" in html
        assert "삼성전자" in html
        assert "SK하이닉스" in html
        assert "background-color: #28a745" in html  # BUY 색상
        assert "background-color: #ffc107" in html  # HOLD 색상
    
    @patch('smtplib.SMTP')
    def test_send_email_notification_success(self, mock_smtp, notification_service, sample_recommendations):
        """이메일 알림 전송 성공 테스트"""
        # Mock SMTP 서버 설정
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # 이메일 활성화 설정
        notification_service.settings.notification_email_enabled = True
        notification_service.settings.notification_email_smtp_server = "smtp.gmail.com"
        notification_service.settings.notification_email_smtp_port = 587
        notification_service.settings.notification_email_user = "test@gmail.com"
        notification_service.settings.notification_email_password = "password"
        notification_service.settings.notification_email_to = ["recipient@gmail.com"]
        
        # 이메일 전송 테스트
        result = notification_service.send_email_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()
    
    def test_send_email_notification_disabled(self, notification_service, sample_recommendations):
        """이메일 알림 비활성화 테스트"""
        # 이메일 비활성화 설정
        notification_service.settings.notification_email_enabled = False
        
        result = notification_service.send_email_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is False
    
    @patch('smtplib.SMTP')
    def test_send_email_notification_failure(self, mock_smtp, notification_service, sample_recommendations):
        """이메일 알림 전송 실패 테스트"""
        # Mock SMTP 서버 설정 (예외 발생)
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        # 이메일 활성화 설정
        notification_service.settings.notification_email_enabled = True
        notification_service.settings.notification_email_smtp_server = "smtp.gmail.com"
        
        result = notification_service.send_email_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is False
    
    @patch('requests.post')
    def test_send_slack_notification_success(self, mock_post, notification_service, sample_recommendations):
        """Slack 알림 전송 성공 테스트"""
        # Mock response 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Slack 활성화 설정
        notification_service.settings.notification_slack_enabled = True
        notification_service.settings.notification_slack_webhook_url = "https://hooks.slack.com/test"
        
        result = notification_service.send_slack_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is True
        mock_post.assert_called_once()
    
    def test_send_slack_notification_disabled(self, notification_service, sample_recommendations):
        """Slack 알림 비활성화 테스트"""
        # Slack 비활성화 설정
        notification_service.settings.notification_slack_enabled = False
        
        result = notification_service.send_slack_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is False
    
    @patch('requests.post')
    def test_send_slack_notification_failure(self, mock_post, notification_service, sample_recommendations):
        """Slack 알림 전송 실패 테스트"""
        # Mock response 설정 (실패)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        # Slack 활성화 설정
        notification_service.settings.notification_slack_enabled = True
        notification_service.settings.notification_slack_webhook_url = "https://hooks.slack.com/test"
        
        result = notification_service.send_slack_notification(
            "테스트 제목", 
            sample_recommendations
        )
        
        assert result is False
    
    def test_format_slack_blocks(self, notification_service, sample_recommendations):
        """Slack 블록 포맷팅 테스트"""
        blocks = notification_service.format_slack_blocks(sample_recommendations)
        
        assert isinstance(blocks, list)
        assert len(blocks) > 0
        
        # 헤더 블록 확인
        header_block = blocks[0]
        assert header_block["type"] == "header"
        assert "📈 주식 추천 리포트" in header_block["text"]["text"]
        
        # 추천 정보 블록들 확인
        for block in blocks[1:]:
            if block["type"] == "section":
                assert "fields" in block
    
    def test_get_recommendation_color(self, notification_service):
        """추천 타입별 색상 테스트"""
        assert notification_service.get_recommendation_color("BUY") == "#28a745"
        assert notification_service.get_recommendation_color("SELL") == "#dc3545"
        assert notification_service.get_recommendation_color("HOLD") == "#ffc107"
        assert notification_service.get_recommendation_color("UNKNOWN") == "#6c757d"
    
    def test_get_recommendation_emoji(self, notification_service):
        """추천 타입별 이모지 테스트"""
        assert notification_service.get_recommendation_emoji("BUY") == "🚀"
        assert notification_service.get_recommendation_emoji("SELL") == "📉"
        assert notification_service.get_recommendation_emoji("HOLD") == "⏸️"
        assert notification_service.get_recommendation_emoji("UNKNOWN") == "❓"
    
    @patch.object(NotificationService, 'send_email_notification')
    @patch.object(NotificationService, 'send_slack_notification')
    def test_send_all_notifications(self, mock_slack, mock_email, notification_service, sample_recommendations):
        """모든 알림 전송 테스트"""
        # Mock 반환값 설정
        mock_email.return_value = True
        mock_slack.return_value = True
        
        results = notification_service.send_all_notifications(
            "테스트 제목", 
            sample_recommendations
        )
        
        # 결과 확인
        assert "email" in results
        assert "slack" in results
        assert results["email"] is True
        assert results["slack"] is True
        
        # 메서드 호출 확인
        mock_email.assert_called_once()
        mock_slack.assert_called_once()
