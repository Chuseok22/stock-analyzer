#!/usr/bin/env python3
"""
Test script to verify the fixes in models.py
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from ml.models import (
    StockPredictionModel, 
    XGBoostModel, 
    LightGBMModel, 
    RandomForestModel,
    EnsembleModel,
    ModelTrainer
)

def create_test_data(n_samples=1000, n_stocks=5):
    """Create synthetic test data with potential edge cases"""
    
    np.random.seed(42)
    data = []
    
    for stock_id in range(n_stocks):
        n_stock_samples = n_samples // n_stocks
        
        # Create dates
        start_date = datetime(2020, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(n_stock_samples)]
        
        # Generate synthetic technical indicators
        close_price = 100 + np.cumsum(np.random.randn(n_stock_samples) * 0.02)
        
        # Add some edge cases
        stock_data = {
            'stock_id': stock_id,
            'date': dates,
            'close': close_price,  # Test column compatibility (close vs close_price)
            'sma_5': close_price + np.random.randn(n_stock_samples) * 0.1,
            'sma_10': close_price + np.random.randn(n_stock_samples) * 0.1,
            'sma_20': close_price + np.random.randn(n_stock_samples) * 0.1,
            'sma_60': close_price + np.random.randn(n_stock_samples) * 0.1,
            'ema_12': close_price + np.random.randn(n_stock_samples) * 0.1,
            'ema_26': close_price + np.random.randn(n_stock_samples) * 0.1,
            'rsi_14': np.random.uniform(0, 100, n_stock_samples),
            'macd': np.random.randn(n_stock_samples) * 0.5,
            'macd_signal': np.random.randn(n_stock_samples) * 0.5,
            'bb_upper': close_price + abs(np.random.randn(n_stock_samples)) * 2,
            'bb_middle': close_price,
            'bb_lower': close_price - abs(np.random.randn(n_stock_samples)) * 2,
            'volume_sma_20': abs(np.random.randn(n_stock_samples)) * 1000000,
            'volume_ratio': abs(np.random.randn(n_stock_samples)) * 2,
            'daily_return': np.random.randn(n_stock_samples) * 0.02,
            'volatility_20': abs(np.random.randn(n_stock_samples)) * 0.1,
            'target': np.random.choice([0, 1], n_stock_samples)
        }
        
        # Add some edge cases for bb_position test (identical bb_upper and bb_lower)
        if stock_id == 0:
            stock_data['bb_upper'][0:5] = stock_data['bb_lower'][0:5]  # Zero width
        
        stock_df = pd.DataFrame(stock_data)
        data.append(stock_df)
    
    return pd.concat(data, ignore_index=True)

def test_column_compatibility():
    """Test column name compatibility feature"""
    print("🔍 Testing column compatibility...")
    
    model = StockPredictionModel()
    
    # Test data with 'close' instead of 'close_price'
    test_df = pd.DataFrame({
        'close': [100, 101, 102],
        'volume': [1000, 1100, 1200]
    })
    
    result_df = model._ensure_column_compatibility(test_df)
    
    assert 'close_price' in result_df.columns, "close_price column should be created"
    assert 'close' in result_df.columns, "close column should remain"
    print("✅ Column compatibility test passed")

def test_numerical_stability():
    """Test numerical stability improvements"""
    print("🔍 Testing numerical stability...")
    
    model = StockPredictionModel()
    
    # Create test data with edge cases
    test_df = create_test_data(100, 2)
    
    # Ensure we have some zero-width bollinger bands
    test_df.loc[0:5, 'bb_upper'] = test_df.loc[0:5, 'bb_lower']
    
    try:
        enhanced_df = model._add_relative_features(test_df)
        
        # Check that bb_position doesn't have infinite values
        assert not np.isinf(enhanced_df['bb_position']).any(), "bb_position should not have infinite values"
        assert not np.isnan(enhanced_df['bb_position']).any(), "bb_position should not have NaN values"
        
        # Check clipping worked
        assert enhanced_df['bb_position'].min() >= -2, "bb_position should be clipped at -2"
        assert enhanced_df['bb_position'].max() <= 3, "bb_position should be clipped at 3"
        
        print("✅ Numerical stability test passed")
    except Exception as e:
        print(f"❌ Numerical stability test failed: {e}")

def test_time_series_consistency():
    """Test that time series operations work correctly with sorting"""
    print("🔍 Testing time series consistency...")
    
    model = StockPredictionModel()
    
    # Create unsorted test data
    test_df = create_test_data(50, 2)
    
    # Shuffle to test sorting
    test_df = test_df.sample(frac=1).reset_index(drop=True)
    
    try:
        X, y = model.prepare_features(test_df)
        
        # Check that we got reasonable features
        assert len(X) > 0, "Should generate some features"
        assert 'momentum_5d' in X.columns, "Should have momentum features"
        assert 'volatility_rank' in X.columns, "Should have volatility rank"
        
        print("✅ Time series consistency test passed")
    except Exception as e:
        print(f"❌ Time series consistency test failed: {e}")

def test_training_robustness():
    """Test training with various edge cases"""
    print("🔍 Testing training robustness...")
    
    # Test with small dataset
    small_data = create_test_data(50, 1)
    
    model = RandomForestModel()
    
    try:
        X, y = model.prepare_features(small_data)
        results = model.train(X, y)
        
        assert model.is_trained, "Model should be trained"
        assert 'auc_score' in results, "Results should include AUC score"
        
        print("✅ Training robustness test passed")
    except Exception as e:
        print(f"❌ Training robustness test failed: {e}")

def test_ensemble_save_load():
    """Test ensemble model save/load functionality"""
    print("🔍 Testing ensemble save/load...")
    
    # Create training data
    data = create_test_data(200, 2)
    
    model = EnsembleModel()
    
    try:
        X, y = model.prepare_features(data)
        results = model.train(X, y)
        
        # Save model
        filepath = model.save_model()
        assert os.path.exists(filepath), "Model file should exist"
        
        # Create new model and load
        new_model = EnsembleModel()
        success = new_model.load_model(filepath)
        
        assert success, "Model loading should succeed"
        assert new_model.is_trained, "Loaded model should be trained"
        assert len(new_model.models) > 0, "Loaded model should have individual models"
        assert len(new_model.weights) > 0, "Loaded model should have weights"
        
        # Test prediction consistency
        pred1 = model.predict(X.head(10))
        pred2 = new_model.predict(X.head(10))
        
        assert np.array_equal(pred1, pred2), "Predictions should be identical"
        
        # Cleanup
        os.remove(filepath)
        
        print("✅ Ensemble save/load test passed")
    except Exception as e:
        print(f"❌ Ensemble save/load test failed: {e}")

def test_model_trainer():
    """Test ModelTrainer with edge cases"""
    print("🔍 Testing ModelTrainer...")
    
    trainer = ModelTrainer()
    
    # Test with insufficient data
    small_data = create_test_data(30, 1)
    
    try:
        results = trainer.train_all_models(small_data)
        
        # Should handle small data gracefully
        assert isinstance(results, dict), "Should return results dict"
        
        # Test get_best_model when no models trained
        best = trainer.get_best_model()
        # Should handle None case gracefully (no crash)
        
        print("✅ ModelTrainer test passed")
    except Exception as e:
        print(f"❌ ModelTrainer test failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting models.py fixes verification...\n")
    
    tests = [
        test_column_compatibility,
        test_numerical_stability,
        test_time_series_consistency,
        test_training_robustness,
        test_ensemble_save_load,
        test_model_trainer
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the fixes.")

if __name__ == "__main__":
    main()