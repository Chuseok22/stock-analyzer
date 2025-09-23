"""
Machine Learning models for stock prediction.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Tuple, Optional, Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from app.config.settings import settings

logger = logging.getLogger(__name__)


class StockPredictionModel:
  """Base class for stock prediction models."""

  def __init__(self, model_name: str = "base_model"):
    self.model_name = model_name
    self.model = None
    self.scaler = None
    self.feature_columns = None
    self.is_trained = False

    # Create model directory if not exists
    self.model_dir = os.path.join(settings.model_cache_dir, model_name)
    os.makedirs(self.model_dir, exist_ok=True)

  def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features and target from raw data.

    Args:
        df: Raw data DataFrame

    Returns:
        Tuple of (features, target)
    """
    # Ensure column name compatibility (close vs close_price)
    df = self._ensure_column_compatibility(df)
    
    # Ensure proper sorting for time series operations
    if 'date' in df.columns and 'stock_id' in df.columns:
      df = df.sort_values(['stock_id', 'date']).reset_index(drop=True)
    
    # Define feature columns (technical indicators)
    feature_cols = [
      'sma_5', 'sma_10', 'sma_20', 'sma_60',
      'ema_12', 'ema_26', 'rsi_14', 'macd', 'macd_signal',
      'bb_upper', 'bb_middle', 'bb_lower',
      'volume_sma_20', 'volume_ratio',
      'daily_return', 'volatility_20'
    ]

    # Add relative features
    df = self._add_relative_features(df)

    # Add additional feature columns
    additional_features = [
      'price_to_sma_20', 'rsi_level', 'macd_histogram',
      'bb_position', 'volume_surge', 'momentum_5d',
      'trend_strength', 'volatility_rank'
    ]

    feature_cols.extend(additional_features)

    # Remove rows with missing features
    features_df = df[feature_cols].copy()
    features_df = features_df.dropna()

    # Get corresponding target values
    target = df.loc[features_df.index, 'target']

    self.feature_columns = feature_cols

    return features_df, target

  def _ensure_column_compatibility(self, df: pd.DataFrame) -> pd.DataFrame:
    """Ensure column name compatibility between different data sources."""
    df = df.copy()
    
    # Handle close vs close_price
    if 'close' in df.columns and 'close_price' not in df.columns:
      df['close_price'] = df['close']
    elif 'close_price' in df.columns and 'close' not in df.columns:
      df['close'] = df['close_price']
    
    # Handle other common variations
    column_mappings = {
      'volume': 'volume',
      'high': 'high_price',
      'low': 'low_price',
      'open': 'open_price'
    }
    
    for alt_name, standard_name in column_mappings.items():
      if alt_name in df.columns and standard_name not in df.columns:
        df[standard_name] = df[alt_name]
      elif standard_name in df.columns and alt_name not in df.columns:
        df[alt_name] = df[standard_name]
    
    return df

  def _add_relative_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add relative and derived features."""
    df = df.copy()
    
    # Small epsilon for numerical stability
    EPS = 1e-8

    # Price relative to moving averages (ensure close_price exists)
    if 'close_price' not in df.columns and 'close' in df.columns:
      df['close_price'] = df['close']
    
    df['price_to_sma_20'] = df['close_price'] / (df['sma_20'] + EPS) - 1

    # RSI levels
    df['rsi_level'] = pd.cut(df['rsi_14'],
                             bins=[0, 30, 70, 100],
                             labels=[0, 1, 2]).astype(float)

    # MACD histogram
    df['macd_histogram'] = df['macd'] - df['macd_signal']

    # Bollinger Band position (with numerical stability)
    bb_width = df['bb_upper'] - df['bb_lower']
    df['bb_position'] = (df['close_price'] - df['bb_lower']) / (bb_width + EPS)
    # Clip to reasonable range
    df['bb_position'] = df['bb_position'].clip(-2, 3)

    # Volume surge indicator (with safety check)
    df['volume_surge'] = (df['volume_ratio'] > 1.5).astype(int)

    # Momentum features (ensure proper grouping)
    if 'stock_id' in df.columns:
      df['momentum_5d'] = df.groupby('stock_id')['close_price'].pct_change(5)
      # Trend strength (slope of SMA)
      df['trend_strength'] = df.groupby('stock_id')['sma_20'].pct_change(5)
      
      # Rolling volatility rank (prevent look-ahead bias)
      df['volatility_rank'] = df.groupby('stock_id')['volatility_20'].apply(
        lambda x: x.rolling(window=60, min_periods=20).rank(pct=True)
      ).reset_index(0, drop=True)
    else:
      # Fallback for single stock
      df['momentum_5d'] = df['close_price'].pct_change(5)
      df['trend_strength'] = df['sma_20'].pct_change(5)
      df['volatility_rank'] = df['volatility_20'].rolling(
        window=60, min_periods=20
      ).rank(pct=True)

    # Fill any remaining NaN values for numerical stability
    for col in ['momentum_5d', 'trend_strength', 'volatility_rank']:
      df[col] = df[col].fillna(0)

    return df

  def train(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> Dict[str, Any]:
    """
    Train the model.

    Args:
        X: Feature DataFrame
        y: Target Series
        test_size: Test set size ratio

    Returns:
        Training results dict
    """
    # Validate input data
    if len(X) == 0 or len(y) == 0:
      raise ValueError("Training data is empty")
    
    if len(X) != len(y):
      raise ValueError(f"Feature and target length mismatch: {len(X)} vs {len(y)}")
    
    # Check for minimum data requirements
    if len(X) < 100:
      logger.warning(f"Small dataset: {len(X)} samples. Results may be unreliable.")
    
    # Check class distribution for stratification
    unique_classes = y.nunique()
    if unique_classes < 2:
      raise ValueError(f"Need at least 2 classes for training, got {unique_classes}")
    
    # Check if stratification is possible
    min_class_size = y.value_counts().min()
    use_stratify = min_class_size >= 2 and test_size > 0
    
    # Split data
    try:
      if use_stratify:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
      else:
        logger.warning("Cannot use stratification due to insufficient class samples")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
    except ValueError as e:
      logger.error(f"Train-test split failed: {e}")
      # Fallback to simple split
      X_train, X_test, y_train, y_test = train_test_split(
          X, y, test_size=test_size, random_state=42
      )

    # Create and train pipeline
    self.scaler = RobustScaler()
    base_model = self._create_model()
    
    # Handle class imbalance for supported models
    if hasattr(base_model, 'class_weight'):
      base_model.set_params(class_weight='balanced')

    pipeline = Pipeline([
      ('scaler', self.scaler),
      ('model', base_model)
    ])

    logger.info(f"Training {self.model_name} on {len(X_train)} samples")

    try:
      # Train model
      pipeline.fit(X_train, y_train)
      
      # Set the trained pipeline BEFORE calculating feature importance
      self.model = pipeline
      self.is_trained = True

      # Evaluate
      train_score = pipeline.score(X_train, y_train)
      test_score = pipeline.score(X_test, y_test)

      # Predictions for detailed metrics
      y_pred = pipeline.predict(X_test)
      y_pred_proba = pipeline.predict_proba(X_test)[:, 1]

      # Calculate metrics
      auc_score = roc_auc_score(y_test, y_pred_proba)

      # Cross validation (with error handling)
      try:
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='roc_auc')
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
      except Exception as e:
        logger.warning(f"Cross-validation failed: {e}")
        cv_mean = cv_std = 0.0

      results = {
        'train_accuracy': train_score,
        'test_accuracy': test_score,
        'auc_score': auc_score,
        'cv_mean': cv_mean,
        'cv_std': cv_std,
        'classification_report': classification_report(y_test, y_pred),
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'feature_importance': self._get_feature_importance(),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'class_distribution': y.value_counts().to_dict()
      }

      logger.info(f"Training completed. Test AUC: {auc_score:.4f}")
      return results

    except Exception as e:
      logger.error(f"Training failed: {e}")
      self.is_trained = False
      raise

  def _create_model(self):
    """Create the base model. Override in subclasses."""
    return RandomForestClassifier(n_estimators=100, random_state=42)

  def _get_feature_importance(self) -> Dict[str, float]:
    """Get feature importance if available."""
    if hasattr(self.model.named_steps['model'], 'feature_importances_'):
      importance = self.model.named_steps['model'].feature_importances_
      return dict(zip(self.feature_columns, importance))
    return { }

  def predict(self, X: pd.DataFrame) -> np.ndarray:
    """Make predictions."""
    if not self.is_trained:
      raise ValueError("Model must be trained before prediction")

    return self.model.predict(X)

  def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
    """Get prediction probabilities."""
    if not self.is_trained:
      raise ValueError("Model must be trained before prediction")

    return self.model.predict_proba(X)

  def save_model(self) -> str:
    """Save model to disk."""
    if not self.is_trained:
      raise ValueError("Model must be trained before saving")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{self.model_name}_{timestamp}.joblib"
    filepath = os.path.join(self.model_dir, filename)

    model_data = {
      'model': self.model,
      'feature_columns': self.feature_columns,
      'model_name': self.model_name,
      'trained_at': timestamp
    }

    joblib.dump(model_data, filepath)
    logger.info(f"Model saved to {filepath}")

    return filepath

  def load_model(self, filepath: str) -> bool:
    """Load model from disk."""
    try:
      model_data = joblib.load(filepath)
      self.model = model_data['model']
      self.feature_columns = model_data['feature_columns']
      self.is_trained = True

      logger.info(f"Model loaded from {filepath}")
      return True

    except Exception as e:
      logger.error(f"Failed to load model: {e}")
      return False


class XGBoostModel(StockPredictionModel):
  """XGBoost model for stock prediction."""

  def __init__(self):
    super().__init__("xgboost")

  def _create_model(self):
    return xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='auc'
    )


class LightGBMModel(StockPredictionModel):
  """LightGBM model for stock prediction."""

  def __init__(self):
    super().__init__("lightgbm")

  def _create_model(self):
    return lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        feature_fraction=0.8,  # More explicit than colsample_bytree
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )


class RandomForestModel(StockPredictionModel):
  """Random Forest model for stock prediction."""

  def __init__(self):
    super().__init__("random_forest")

  def _create_model(self):
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42
    )


class EnsembleModel(StockPredictionModel):
  """Ensemble model combining multiple algorithms."""

  def __init__(self):
    super().__init__("ensemble")
    self.models = { }
    self.weights = { }

  def train(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> Dict[str, Any]:
    """Train ensemble of models."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    # Define models
    models_config = {
      'xgb': xgb.XGBClassifier(n_estimators=100, random_state=42),
      'lgb': lgb.LGBMClassifier(n_estimators=100, random_state=42, verbose=-1),
      'rf': RandomForestClassifier(n_estimators=100, random_state=42)
    }

    # Train individual models
    model_scores = { }

    for name, model in models_config.items():
      logger.info(f"Training {name} model")

      pipeline = Pipeline([
        ('scaler', RobustScaler()),
        ('model', model)
      ])

      pipeline.fit(X_train, y_train)

      # Evaluate
      y_pred_proba = pipeline.predict_proba(X_test)[:, 1]
      auc = roc_auc_score(y_test, y_pred_proba)

      self.models[name] = pipeline
      model_scores[name] = auc

      logger.info(f"{name} AUC: {auc:.4f}")

    # Calculate weights based on performance
    total_score = sum(model_scores.values())
    self.weights = { name: score / total_score for name, score in model_scores.items() }

    # Ensemble predictions
    ensemble_proba = self._ensemble_predict_proba(X_test)
    ensemble_pred = (ensemble_proba >= 0.5).astype(int)

    ensemble_auc = roc_auc_score(y_test, ensemble_proba)
    ensemble_accuracy = (ensemble_pred == y_test).mean()

    self.feature_columns = list(X.columns)
    self.is_trained = True

    results = {
      'individual_scores': model_scores,
      'weights': self.weights,
      'ensemble_auc': ensemble_auc,
      'ensemble_accuracy': ensemble_accuracy,
      'test_size': len(X_test)
    }

    logger.info(f"Ensemble training completed. AUC: {ensemble_auc:.4f}")

    return results

  def _ensemble_predict_proba(self, X: pd.DataFrame) -> np.ndarray:
    """Get ensemble prediction probabilities."""
    predictions = []

    for name, model in self.models.items():
      pred_proba = model.predict_proba(X)[:, 1]
      weighted_pred = pred_proba * self.weights[name]
      predictions.append(weighted_pred)

    return np.sum(predictions, axis=0)

  def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
    """Get ensemble prediction probabilities."""
    if not self.is_trained:
      raise ValueError("Model must be trained before prediction")

    proba = self._ensemble_predict_proba(X)
    return np.column_stack([1 - proba, proba])

  def predict(self, X: pd.DataFrame) -> np.ndarray:
    """Make ensemble predictions."""
    proba = self._ensemble_predict_proba(X)
    return (proba >= 0.5).astype(int)

  def save_model(self) -> str:
    """Save ensemble model to disk."""
    if not self.is_trained:
      raise ValueError("Model must be trained before saving")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{self.model_name}_{timestamp}.joblib"
    filepath = os.path.join(self.model_dir, filename)

    model_data = {
      'models': self.models,  # Save individual models dict
      'weights': self.weights,  # Save model weights
      'feature_columns': self.feature_columns,
      'model_name': self.model_name,
      'trained_at': timestamp
    }

    joblib.dump(model_data, filepath)
    logger.info(f"Ensemble model saved to {filepath}")

    return filepath

  def load_model(self, filepath: str) -> bool:
    """Load ensemble model from disk."""
    try:
      model_data = joblib.load(filepath)
      self.models = model_data['models']
      self.weights = model_data['weights']
      self.feature_columns = model_data['feature_columns']
      self.is_trained = True

      logger.info(f"Ensemble model loaded from {filepath}")
      return True

    except Exception as e:
      logger.error(f"Failed to load ensemble model: {e}")
      return False


class ModelTrainer:
  """Model training and evaluation coordinator."""

  def __init__(self):
    self.models = {
      'xgboost': XGBoostModel(),
      'lightgbm': LightGBMModel(),
      'random_forest': RandomForestModel(),
      'ensemble': EnsembleModel()
    }
    self.best_model = None
    self.best_score = 0.0

  def train_all_models(self, training_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Train all models and select the best one.

    Args:
        training_data: Training dataset

    Returns:
        Training results for all models
    """
    if training_data.empty:
      raise ValueError("Training data is empty")

    logger.info(f"Training models on {len(training_data)} samples")

    results = { }

    for name, model in self.models.items():
      try:
        logger.info(f"Training {name} model")

        # Prepare features
        X, y = model.prepare_features(training_data)

        if len(X) < 100:  # Minimum data requirement
          logger.warning(f"Insufficient data for {name}: {len(X)} samples")
          continue

        # Train model
        model_results = model.train(X, y)
        results[name] = model_results

        # Track best model
        auc_score = model_results.get('auc_score', 0)
        if auc_score > self.best_score:
          self.best_score = auc_score
          self.best_model = model

        # Save model
        model.save_model()

      except Exception as e:
        logger.error(f"Failed to train {name}: {e}")
        results[name] = { 'error': str(e) }

    # Ensure we have a best model
    if self.best_model is None:
      logger.warning("No models were successfully trained")
      return results

    logger.info(f"Best model: {self.best_model.model_name} (AUC: {self.best_score:.4f})")

    return results

  def get_best_model(self) -> Optional[StockPredictionModel]:
    """Get the best performing model."""
    if self.best_model is None:
      logger.warning("No best model available. Train models first.")
    return self.best_model
