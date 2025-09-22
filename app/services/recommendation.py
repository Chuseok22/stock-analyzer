"""
Stock recommendation system using ML predictions.
"""
import json
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional

import pandas as pd
from sqlalchemy import and_

from app.database.connection import get_db_session
from app.ml.models import ModelTrainer
from app.models.entities import Stock, UniverseItem, Recommendation, StockIndicator, StockPrice
from app.services.data_collection import DataCollectionService
from app.utils.data_utils import DateUtils, DataFrameUtils
from app.utils.database_utils import DatabaseUtils

logger = logging.getLogger(__name__)


class RecommendationService:
  """Service for generating stock recommendations."""

  def __init__(self):
    self.data_service = DataCollectionService()
    self.model_trainer = ModelTrainer()
    self.current_model = None

  def train_model(self, universe_id: int, retrain: bool = False) -> Dict[str, any]:
    """
    Train or retrain the prediction model.

    Args:
        universe_id: Universe to train on
        retrain: Force retraining even if model exists

    Returns:
        Training results
    """
    try:
      logger.info(f"Starting model training for universe {universe_id}")

      # Get training data
      training_data = self.data_service.get_training_data(
          universe_id=universe_id,
          lookback_days=252  # 1 year of data
      )

      if training_data.empty:
        raise ValueError("No training data available")

      # Train models
      training_results = self.model_trainer.train_all_models(training_data)

      # Set current model to best performing one
      self.current_model = self.model_trainer.get_best_model()

      logger.info("Model training completed successfully")

      return {
        'success': True,
        'training_results': training_results,
        'best_model': self.current_model.model_name if self.current_model else None,
        'training_samples': len(training_data)
      }

    except Exception as e:
      logger.error(f"Model training failed: {e}")
      return {
        'success': False,
        'error': str(e)
      }

  def generate_recommendations(self, universe_id: int, target_date: date = None,
      top_n: int = 20) -> List[Dict]:
    """
    Generate stock recommendations for a given date.

    Args:
        universe_id: Universe to generate recommendations for
        target_date: Date to generate recommendations for (default: tomorrow)
        top_n: Number of top recommendations to return

    Returns:
        List of recommendation dictionaries
    """
    if not self.current_model or not self.current_model.is_trained:
      raise ValueError("Model must be trained before generating recommendations")

    if target_date is None:
      target_date = DateUtils.get_next_trading_day(date.today())

    try:
      logger.info(f"Generating recommendations for {target_date}")

      # Get current features for all stocks in universe
      features_data = self._get_current_features(universe_id, target_date)

      if features_data.empty:
        logger.warning("No feature data available for recommendations")
        return []

      # Make predictions
      predictions = self._make_predictions(features_data)

      # Rank and select top recommendations
      recommendations = self._rank_predictions(predictions, top_n)

      # Save recommendations to database
      self._save_recommendations(universe_id, target_date, recommendations)

      logger.info(f"Generated {len(recommendations)} recommendations")

      return recommendations

    except Exception as e:
      logger.error(f"Failed to generate recommendations: {e}")
      return []

  def _get_current_features(self, universe_id: int, target_date: date) -> pd.DataFrame:
    """Get current features for stocks in universe with improved date handling."""
    # Use DateUtils for proper trading day calculation
    feature_date = DateUtils.get_previous_trading_day(target_date)

    with DatabaseUtils.safe_db_session() as db:
      # Get stocks in universe using DatabaseUtils
      stock_ids = DatabaseUtils.get_stock_ids_in_universe(db, universe_id)

      if not stock_ids:
        logger.warning(f"No stocks found in universe {universe_id}")
        return pd.DataFrame()

      # Query latest indicators with improved error handling
      query = db.query(
          StockIndicator.stock_id,
          Stock.code.label('stock_code'),
          Stock.name.label('stock_name'),
          StockIndicator.sma_5,
          StockIndicator.sma_10,
          StockIndicator.sma_20,
          StockIndicator.sma_60,
          StockIndicator.ema_12,
          StockIndicator.ema_26,
          StockIndicator.rsi_14,
          StockIndicator.macd,
          StockIndicator.macd_signal,
          StockIndicator.bb_upper,
          StockIndicator.bb_middle,
          StockIndicator.bb_lower,
          StockIndicator.volume_sma_20,
          StockIndicator.volume_ratio,
          StockIndicator.daily_return,
          StockIndicator.volatility_20,
          StockPrice.close_price
      ).join(
          Stock, StockIndicator.stock_id == Stock.id
      ).join(
          StockPrice, and_(
              StockIndicator.stock_id == StockPrice.stock_id,
              StockIndicator.trade_date == StockPrice.trade_date
          )
      ).filter(
          and_(
              StockIndicator.stock_id.in_(stock_ids),
              StockIndicator.trade_date == feature_date
          )
      )

      df = pd.read_sql(query.statement, db.bind)

      if not df.empty:
        # Add derived features using DataFrameUtils
        df = DataFrameUtils.add_technical_features(df)
        
        # Clean the dataframe
        numeric_columns = [
          'sma_5', 'sma_10', 'sma_20', 'sma_60', 'ema_12', 'ema_26', 'rsi_14',
          'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
          'volume_sma_20', 'volume_ratio', 'daily_return', 'volatility_20',
          'close_price'
        ]
        df = DataFrameUtils.clean_dataframe(df, numeric_columns=numeric_columns)

      return df

  def _make_predictions(self, features_data: pd.DataFrame) -> pd.DataFrame:
    """Make predictions using the trained model."""
    # Prepare features for prediction
    feature_columns = self.current_model.feature_columns

    # Ensure all required columns exist
    missing_cols = set(feature_columns) - set(features_data.columns)
    for col in missing_cols:
      features_data[col] = 0  # Default value for missing features

    X = features_data[feature_columns].fillna(0)

    # Get predictions
    probabilities = self.current_model.predict_proba(X)
    predictions = self.current_model.predict(X)

    # Add predictions to dataframe
    result = features_data.copy()
    result['prediction_score'] = probabilities[:, 1]  # Probability of positive class
    result['prediction'] = predictions

    return result

  def _rank_predictions(self, predictions: pd.DataFrame, top_n: int) -> List[Dict]:
    """Rank predictions and return top recommendations."""
    # Filter positive predictions
    positive_predictions = predictions[predictions['prediction'] == 1].copy()

    if positive_predictions.empty:
      logger.warning("No positive predictions found")
      return []

    # Sort by prediction score
    ranked = positive_predictions.sort_values('prediction_score', ascending=False)

    # Take top N
    top_recommendations = ranked.head(top_n)

    recommendations = []
    for i, (_, row) in enumerate(top_recommendations.iterrows()):
      reason = self._generate_reason(row)

      recommendation = {
        'stock_id': int(row['stock_id']),
        'stock_code': row['stock_code'],
        'stock_name': row['stock_name'],
        'score': float(row['prediction_score']),
        'rank': i + 1,
        'reason': reason,
        'features': {
          'rsi_14': float(row['rsi_14']) if pd.notna(row['rsi_14']) else None,
          'price_to_sma_20': float(row['price_to_sma_20']) if pd.notna(row['price_to_sma_20']) else None,
          'volume_ratio': float(row['volume_ratio']) if pd.notna(row['volume_ratio']) else None,
          'macd_signal': 'positive' if row['macd'] > row['macd_signal'] else 'negative'
        }
      }
      recommendations.append(recommendation)

    return recommendations

  def _generate_reason(self, row: pd.Series) -> Dict:
    """Generate human-readable reason for recommendation."""
    reasons = []

    # RSI analysis
    rsi = row['rsi_14']
    if pd.notna(rsi):
      if rsi < 30:
        reasons.append("RSI indicates oversold condition")
      elif rsi > 70:
        reasons.append("RSI shows strong momentum")
      else:
        reasons.append("RSI in neutral zone")

    # Price vs SMA
    price_to_sma = row['price_to_sma_20']
    if pd.notna(price_to_sma):
      if price_to_sma > 0.02:
        reasons.append("Price above 20-day moving average")
      elif price_to_sma < -0.02:
        reasons.append("Price below 20-day moving average - potential value")

    # Volume analysis
    volume_ratio = row['volume_ratio']
    if pd.notna(volume_ratio) and volume_ratio > 1.5:
      reasons.append("High volume activity detected")

    # MACD analysis
    if pd.notna(row['macd']) and pd.notna(row['macd_signal']):
      if row['macd'] > row['macd_signal']:
        reasons.append("MACD shows bullish signal")
      else:
        reasons.append("MACD shows bearish signal")

    return {
      'summary': "Machine learning model predicts positive price movement",
      'technical_factors': reasons,
      'confidence': float(row['prediction_score'])
    }

  def _save_recommendations(self, universe_id: int, target_date: date,
      recommendations: List[Dict]) -> None:
    """Save recommendations to database."""
    with get_db_session() as db:
      for rec in recommendations:
        # Check if recommendation already exists
        existing = db.query(Recommendation).filter(
            and_(
                Recommendation.stock_id == rec['stock_id'],
                Recommendation.for_date == target_date
            )
        ).first()

        reason_json = json.dumps(rec['reason'], ensure_ascii=False)

        if existing:
          # Update existing recommendation
          existing.universe_id = universe_id
          existing.score = rec['score']
          existing.rank = rec['rank']
          existing.reason_json = reason_json
        else:
          # Create new recommendation
          recommendation = Recommendation(
              stock_id=rec['stock_id'],
              universe_id=universe_id,
              for_date=target_date,
              score=rec['score'],
              rank=rec['rank'],
              reason_json=reason_json
          )
          db.add(recommendation)

  def get_historical_performance(self, days: int = 30) -> Dict:
    """
    Analyze historical performance of recommendations.

    Args:
        days: Number of days to analyze

    Returns:
        Performance metrics
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    try:
      with get_db_session() as db:
        # Get historical recommendations
        recommendations = db.query(Recommendation).filter(
            and_(
                Recommendation.for_date >= start_date,
                Recommendation.for_date < end_date
            )
        ).order_by(
            Recommendation.for_date,
            Recommendation.rank
        ).all()

        if not recommendations:
          return { 'error': 'No historical recommendations found' }

        # Calculate performance for each recommendation
        performance_data = []

        for rec in recommendations:
          perf = self._calculate_recommendation_performance(rec)
          if perf:
            performance_data.append(perf)

        if not performance_data:
          return { 'error': 'No performance data available' }

        # Aggregate metrics
        df = pd.DataFrame(performance_data)

        metrics = {
          'total_recommendations': len(df),
          'avg_return_1d': df['return_1d'].mean(),
          'avg_return_3d': df['return_3d'].mean(),
          'avg_return_7d': df['return_7d'].mean(),
          'success_rate_1d': (df['return_1d'] > 0).mean(),
          'success_rate_3d': (df['return_3d'] > 0).mean(),
          'success_rate_7d': (df['return_7d'] > 0).mean(),
          'best_performing': {
            'stock_code': df.loc[df['return_7d'].idxmax(), 'stock_code'],
            'return_7d': df['return_7d'].max()
          },
          'worst_performing': {
            'stock_code': df.loc[df['return_7d'].idxmin(), 'stock_code'],
            'return_7d': df['return_7d'].min()
          }
        }

        return metrics

    except Exception as e:
      logger.error(f"Failed to calculate historical performance: {e}")
      return { 'error': str(e) }

  def _calculate_recommendation_performance(self, rec: Recommendation) -> Optional[Dict]:
    """Calculate performance metrics for a single recommendation."""
    try:
      with get_db_session() as db:
        # Get stock code
        stock = db.query(Stock).filter(Stock.id == rec.stock_id).first()
        if not stock:
          return None

        # Get price on recommendation date
        base_price = db.query(StockPrice).filter(
            and_(
                StockPrice.stock_id == rec.stock_id,
                StockPrice.trade_date == rec.for_date
            )
        ).first()

        if not base_price:
          return None

        # Calculate returns for different periods
        returns = { }

        for days in [1, 3, 7]:
          future_date = rec.for_date + timedelta(days=days)

          # Find next available trading day
          future_price = db.query(StockPrice).filter(
              and_(
                  StockPrice.stock_id == rec.stock_id,
                  StockPrice.trade_date >= future_date
              )
          ).order_by(StockPrice.trade_date).first()

          if future_price:
            ret = (future_price.close_price - base_price.close_price) / base_price.close_price
            returns[f'return_{days}d'] = ret
          else:
            returns[f'return_{days}d'] = None

        return {
          'stock_code': stock.code,
          'recommendation_date': rec.for_date,
          'score': rec.score,
          'rank': rec.rank,
          **returns
        }

    except Exception as e:
      logger.error(f"Failed to calculate performance for recommendation {rec.id}: {e}")
      return None
