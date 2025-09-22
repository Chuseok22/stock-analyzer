"""
Main entry point for stock analysis and recommendation system.
This script can be called from Spring Boot scheduler.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, date
from typing import Dict, Any
import json

# Add app directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.database.connection import init_db
from app.services.data_collection import DataCollectionService
from app.services.recommendation import RecommendationService
from app.utils.logger import setup_logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(description='Stock Analysis and Recommendation System')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Data collection command
    collect_parser = subparsers.add_parser('collect', help='Collect stock data')
    collect_parser.add_argument('--universe-id', type=int, required=True,
                               help='Universe ID to collect data for')
    collect_parser.add_argument('--days', type=int, default=252,
                               help='Number of days to collect (default: 252)')
    
    # Update universe command
    universe_parser = subparsers.add_parser('update-universe', help='Update stock universe')
    universe_parser.add_argument('--region', default='KR', choices=['KR', 'US'],
                                help='Market region (default: KR)')
    universe_parser.add_argument('--top-n', type=int, default=200,
                                help='Number of top stocks to include (default: 200)')
    
    # Train model command
    train_parser = subparsers.add_parser('train', help='Train ML model')
    train_parser.add_argument('--universe-id', type=int, required=True,
                             help='Universe ID to train on')
    train_parser.add_argument('--retrain', action='store_true',
                             help='Force retrain even if model exists')
    
    # Generate recommendations command
    recommend_parser = subparsers.add_parser('recommend', help='Generate recommendations')
    recommend_parser.add_argument('--universe-id', type=int, required=True,
                                 help='Universe ID to generate recommendations for')
    recommend_parser.add_argument('--date', type=str,
                                 help='Target date (YYYY-MM-DD), default: tomorrow')
    recommend_parser.add_argument('--top-n', type=int, default=20,
                                 help='Number of recommendations (default: 20)')
    
    # Full pipeline command (most common use case)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run full pipeline')
    pipeline_parser.add_argument('--universe-id', type=int, required=True,
                                help='Universe ID to process')
    pipeline_parser.add_argument('--collect-data', action='store_true',
                                help='Collect fresh data before processing')
    pipeline_parser.add_argument('--retrain', action='store_true',
                                help='Retrain model before recommendations')
    pipeline_parser.add_argument('--top-n', type=int, default=20,
                                help='Number of recommendations (default: 20)')
    
    # Performance analysis command
    perf_parser = subparsers.add_parser('performance', help='Analyze recommendation performance')
    perf_parser.add_argument('--days', type=int, default=30,
                            help='Number of days to analyze (default: 30)')
    
    return parser


def collect_data_command(args) -> Dict[str, Any]:
    """Execute data collection command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting data collection for universe {args.universe_id}")
    
    try:
        data_service = DataCollectionService()
        
        # Get stocks in universe and collect their data
        with data_service.get_db_session() as db:
            from app.models.entities import UniverseItem, Stock
            
            universe_stocks = db.query(UniverseItem).filter(
                UniverseItem.universe_id == args.universe_id
            ).all()
            
            stock_codes = []
            for item in universe_stocks:
                stock = db.query(Stock).filter(Stock.id == item.stock_id).first()
                if stock and stock.active:
                    stock_codes.append(stock.code)
        
        if not stock_codes:
            return {'success': False, 'error': 'No stocks found in universe'}
        
        # Collect price data
        success = data_service.collect_stock_prices(stock_codes, args.days)
        
        if success:
            # Calculate technical indicators
            data_service.calculate_technical_indicators()
            
            return {
                'success': True,
                'stocks_processed': len(stock_codes),
                'days_collected': args.days
            }
        else:
            return {'success': False, 'error': 'Failed to collect stock data'}
            
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        return {'success': False, 'error': str(e)}


def update_universe_command(args) -> Dict[str, Any]:
    """Execute universe update command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Updating universe for {args.region} market")
    
    try:
        data_service = DataCollectionService()
        universe_id = data_service.update_universe_stocks(args.region, args.top_n)
        
        if universe_id:
            return {
                'success': True,
                'universe_id': universe_id,
                'region': args.region,
                'stocks_count': args.top_n
            }
        else:
            return {'success': False, 'error': 'Failed to update universe'}
            
    except Exception as e:
        logger.error(f"Universe update failed: {e}")
        return {'success': False, 'error': str(e)}


def train_model_command(args) -> Dict[str, Any]:
    """Execute model training command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Training model for universe {args.universe_id}")
    
    try:
        rec_service = RecommendationService()
        result = rec_service.train_model(args.universe_id, args.retrain)
        
        return result
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return {'success': False, 'error': str(e)}


def recommend_command(args) -> Dict[str, Any]:
    """Execute recommendation generation command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Generating recommendations for universe {args.universe_id}")
    
    try:
        rec_service = RecommendationService()
        
        # Parse target date
        target_date = None
        if args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        
        recommendations = rec_service.generate_recommendations(
            args.universe_id, target_date, args.top_n
        )
        
        return {
            'success': True,
            'recommendations_count': len(recommendations),
            'recommendations': recommendations[:5],  # Return top 5 for output
            'target_date': target_date.isoformat() if target_date else None
        }
        
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        return {'success': False, 'error': str(e)}


def pipeline_command(args) -> Dict[str, Any]:
    """Execute full pipeline command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Running full pipeline for universe {args.universe_id}")
    
    results = {}
    
    try:
        # Step 1: Collect data if requested
        if args.collect_data:
            logger.info("Step 1: Collecting data")
            collect_args = argparse.Namespace(
                universe_id=args.universe_id,
                days=252
            )
            results['data_collection'] = collect_data_command(collect_args)
            
            if not results['data_collection']['success']:
                return results
        
        # Step 2: Train model if requested
        if args.retrain:
            logger.info("Step 2: Training model")
            train_args = argparse.Namespace(
                universe_id=args.universe_id,
                retrain=True
            )
            results['model_training'] = train_model_command(train_args)
            
            if not results['model_training']['success']:
                return results
        
        # Step 3: Generate recommendations
        logger.info("Step 3: Generating recommendations")
        recommend_args = argparse.Namespace(
            universe_id=args.universe_id,
            date=None,
            top_n=args.top_n
        )
        results['recommendations'] = recommend_command(recommend_args)
        
        return results
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        results['error'] = str(e)
        return results


def performance_command(args) -> Dict[str, Any]:
    """Execute performance analysis command."""
    logger = logging.getLogger(__name__)
    logger.info(f"Analyzing performance for last {args.days} days")
    
    try:
        rec_service = RecommendationService()
        performance = rec_service.get_historical_performance(args.days)
        
        return {
            'success': True,
            'performance_metrics': performance
        }
        
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database connection
    try:
        init_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return
    
    # Execute command
    start_time = datetime.now()
    logger.info(f"Executing command: {args.command}")
    
    try:
        if args.command == 'collect':
            result = collect_data_command(args)
        elif args.command == 'update-universe':
            result = update_universe_command(args)
        elif args.command == 'train':
            result = train_model_command(args)
        elif args.command == 'recommend':
            result = recommend_command(args)
        elif args.command == 'pipeline':
            result = pipeline_command(args)
        elif args.command == 'performance':
            result = performance_command(args)
        else:
            result = {'success': False, 'error': f'Unknown command: {args.command}'}
        
        # Log execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        result['execution_time_seconds'] = execution_time
        
        # Output result as JSON for easy parsing by Spring Boot
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        
        # Set exit code based on success
        exit_code = 0 if result.get('success', False) else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        error_result = {
            'success': False,
            'error': str(e),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
