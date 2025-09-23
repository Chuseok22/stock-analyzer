"""
주식 분석 시스템 데이터베이스 모델 테스트
"""
import sys
from pathlib import Path

# app 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.entities import Base, StockMaster, StockDailyPrice
import os


class TestModels:
    """데이터베이스 모델 테스트 클래스"""
    
    @pytest.fixture(scope="class")
    def engine(self):
        """테스트용 데이터베이스 엔진"""
        database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://test_user:test_password@localhost:5432/test_stock_analyzer"
        )
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)
    
    @pytest.fixture
    def session(self, engine):
        """테스트용 데이터베이스 세션"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_stock_model(self, session):
        """Stock 모델 테스트"""
        stock = Stock(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            sector="IT",
            is_active=True
        )
        
        session.add(stock)
        session.commit()
        
        saved_stock = session.query(Stock).filter_by(code="005930").first()
        assert saved_stock is not None
        assert saved_stock.name == "삼성전자"
        assert saved_stock.market == "KOSPI"
        assert saved_stock.sector == "IT"
        assert saved_stock.is_active is True
    
    def test_stock_data_model(self, session):
        """StockData 모델 테스트"""
        # 먼저 Stock 생성
        stock = Stock(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            sector="IT",
            is_active=True
        )
        session.add(stock)
        session.flush()
        
        # StockData 생성
        stock_data = StockData(
            stock_id=stock.id,
            date=date.today(),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("70500"),
            volume=1000000,
            trading_value=Decimal("70500000000")
        )
        
        session.add(stock_data)
        session.commit()
        
        saved_data = session.query(StockData).filter_by(stock_id=stock.id).first()
        assert saved_data is not None
        assert saved_data.open_price == Decimal("70000")
        assert saved_data.close_price == Decimal("70500")
        assert saved_data.volume == 1000000
    
    def test_stock_recommendation_model(self, session):
        """StockRecommendation 모델 테스트"""
        # 먼저 Stock 생성
        stock = Stock(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            sector="IT",
            is_active=True
        )
        session.add(stock)
        session.flush()
        
        # StockRecommendation 생성
        recommendation = StockRecommendation(
            stock_id=stock.id,
            recommendation_date=date.today(),
            recommendation_type="BUY",
            confidence_score=Decimal("0.85"),
            target_price=Decimal("75000"),
            reasoning="강한 상승 신호 감지"
        )
        
        session.add(recommendation)
        session.commit()
        
        saved_rec = session.query(StockRecommendation).filter_by(stock_id=stock.id).first()
        assert saved_rec is not None
        assert saved_rec.recommendation_type == "BUY"
        assert saved_rec.confidence_score == Decimal("0.85")
        assert saved_rec.target_price == Decimal("75000")
    
    def test_ml_model_model(self, session):
        """MLModel 모델 테스트"""
        ml_model = MLModel(
            name="XGBoost_Classifier",
            version="1.0",
            model_type="classification",
            parameters={"n_estimators": 100, "max_depth": 6},
            accuracy=Decimal("0.85"),
            is_active=True
        )
        
        session.add(ml_model)
        session.commit()
        
        saved_model = session.query(MLModel).filter_by(name="XGBoost_Classifier").first()
        assert saved_model is not None
        assert saved_model.version == "1.0"
        assert saved_model.model_type == "classification"
        assert saved_model.accuracy == Decimal("0.85")
        assert saved_model.is_active is True
    
    def test_stock_relationship(self, session):
        """Stock과 관련 모델들의 관계 테스트"""
        # Stock 생성
        stock = Stock(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            sector="IT",
            is_active=True
        )
        session.add(stock)
        session.flush()
        
        # StockData 생성
        stock_data = StockData(
            stock_id=stock.id,
            date=date.today(),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("70500"),
            volume=1000000,
            trading_value=Decimal("70500000000")
        )
        
        # StockRecommendation 생성
        recommendation = StockRecommendation(
            stock_id=stock.id,
            recommendation_date=date.today(),
            recommendation_type="BUY",
            confidence_score=Decimal("0.85"),
            target_price=Decimal("75000"),
            reasoning="강한 상승 신호 감지"
        )
        
        session.add_all([stock_data, recommendation])
        session.commit()
        
        # 관계 확인
        saved_stock = session.query(Stock).filter_by(code="005930").first()
        assert len(saved_stock.stock_data) == 1
        assert len(saved_stock.recommendations) == 1
        assert saved_stock.stock_data[0].close_price == Decimal("70500")
        assert saved_stock.recommendations[0].recommendation_type == "BUY"
