"""
주식 분석 시스템 KIS API 서비스 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.kis_api import KISApiService
import asyncio
import os


class TestKISApiService:
    """KIS API 서비스 테스트 클래스"""
    
    @pytest.fixture
    def kis_service(self):
        """KIS API 서비스 인스턴스"""
        return KISApiService()
    
    @pytest.fixture
    def mock_token_response(self):
        """모킹된 토큰 응답"""
        return {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 86400
        }
    
    @pytest.fixture
    def mock_stock_data_response(self):
        """모킹된 주식 데이터 응답"""
        return {
            "output": {
                "stck_prpr": "70500",  # 현재가
                "prdy_vrss": "500",    # 전일대비
                "prdy_vrss_sign": "2", # 대비부호
                "prdy_ctrt": "0.71",   # 등락률
                "acml_vol": "1000000", # 누적거래량
                "acml_tr_pbmn": "70500000000"  # 누적거래대금
            }
        }
    
    def test_service_initialization(self, kis_service):
        """서비스 초기화 테스트"""
        assert kis_service.app_key == "test_key"
        assert kis_service.secret_key == "test_secret"
        assert kis_service.base_url == "https://openapi.koreainvestment.com:9443"
        assert kis_service.access_token is None
    
    @patch('aiohttp.ClientSession.post')
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, mock_post, kis_service, mock_token_response):
        """액세스 토큰 획득 성공 테스트"""
        # Mock response 설정
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 토큰 획득 테스트
        token = await kis_service.get_access_token()
        
        assert token == "test_access_token"
        assert kis_service.access_token == "test_access_token"
        mock_post.assert_called_once()
    
    @patch('aiohttp.ClientSession.post')
    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, mock_post, kis_service):
        """액세스 토큰 획득 실패 테스트"""
        # Mock response 설정 (실패)
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 토큰 획득 실패 테스트
        with pytest.raises(Exception) as exc_info:
            await kis_service.get_access_token()
        
        assert "Failed to get access token" in str(exc_info.value)
    
    @patch('aiohttp.ClientSession.get')
    @pytest.mark.asyncio
    async def test_get_stock_data_success(self, mock_get, kis_service, mock_stock_data_response):
        """주식 데이터 조회 성공 테스트"""
        # 토큰 설정
        kis_service.access_token = "test_access_token"
        
        # Mock response 설정
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_stock_data_response)
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # 주식 데이터 조회 테스트
        data = await kis_service.get_stock_data("005930")
        
        assert data is not None
        assert "output" in data
        assert data["output"]["stck_prpr"] == "70500"
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    @pytest.mark.asyncio
    async def test_get_stock_data_no_token(self, mock_get, kis_service):
        """토큰 없이 주식 데이터 조회 테스트"""
        # 토큰 미설정 상태에서 테스트
        kis_service.access_token = None
        
        with pytest.raises(Exception) as exc_info:
            await kis_service.get_stock_data("005930")
        
        assert "Access token not available" in str(exc_info.value)
    
    @patch('aiohttp.ClientSession.get')
    @pytest.mark.asyncio
    async def test_get_stock_data_api_error(self, mock_get, kis_service):
        """API 오류 시 주식 데이터 조회 테스트"""
        # 토큰 설정
        kis_service.access_token = "test_access_token"
        
        # Mock response 설정 (API 오류)
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            await kis_service.get_stock_data("005930")
        
        assert "Failed to get stock data" in str(exc_info.value)
    
    def test_format_stock_code(self, kis_service):
        """주식 코드 포맷팅 테스트"""
        # 6자리 코드 테스트
        assert kis_service.format_stock_code("005930") == "005930"
        
        # 짧은 코드 테스트 (0 패딩)
        assert kis_service.format_stock_code("5930") == "005930"
        assert kis_service.format_stock_code("30") == "000030"
        
        # 긴 코드 테스트 (그대로 반환)
        assert kis_service.format_stock_code("1234567") == "1234567"
    
    @pytest.mark.asyncio
    async def test_validate_connection(self, kis_service):
        """연결 검증 테스트"""
        with patch.object(kis_service, 'get_access_token') as mock_get_token:
            mock_get_token.return_value = "test_token"
            
            result = await kis_service.validate_connection()
            assert result is True
            mock_get_token.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, kis_service):
        """연결 검증 실패 테스트"""
        with patch.object(kis_service, 'get_access_token') as mock_get_token:
            mock_get_token.side_effect = Exception("Connection failed")
            
            result = await kis_service.validate_connection()
            assert result is False
