#!/usr/bin/env python3
"""
Environment variable validation script
.env 파일과 .env.example 파일을 비교하고 설정 검증
"""

import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
import logging

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

def load_env_file(file_path: Path) -> Dict[str, str]:
    """환경 변수 파일을 로드하여 딕셔너리로 반환"""
    env_vars = {}
    
    if not file_path.exists():
        return env_vars
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 주석이나 빈 줄 무시
            if not line or line.startswith('#'):
                continue
            
            # KEY=VALUE 형태 파싱
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def validate_env_files() -> Tuple[bool, List[str]]:
    """환경 변수 파일들을 검증하고 문제점을 반환"""
    issues = []
    
    # 파일 경로
    env_file = PROJECT_ROOT / '.env'
    env_example_file = PROJECT_ROOT / '.env.example'
    
    # 파일 존재 확인
    if not env_file.exists():
        issues.append("❌ .env 파일이 존재하지 않습니다.")
        return False, issues
    
    if not env_example_file.exists():
        issues.append("❌ .env.example 파일이 존재하지 않습니다.")
        return False, issues
    
    # 환경 변수 로드
    env_vars = load_env_file(env_file)
    example_vars = load_env_file(env_example_file)
    
    print(f"📋 .env 파일에서 {len(env_vars)}개의 환경 변수를 찾았습니다.")
    print(f"📋 .env.example 파일에서 {len(example_vars)}개의 환경 변수를 찾았습니다.")
    
    # 필수 환경 변수 정의
    required_vars = {
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_BASE_URL',
        'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB',
        'ALPHA_VANTAGE_API_KEY',
        'DISCORD_WEBHOOK_URL'
    }
    
    # 선택적 환경 변수 정의
    optional_vars = {
        'SMTP_ENABLED', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USE_TLS',
        'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_FROM_EMAIL', 'NOTIFICATION_EMAIL',
        'SLACK_ENABLED', 'SLACK_TOKEN', 'SLACK_CHANNEL',
        'TELEGRAM_ENABLED', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
        'SECRET_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY'
    }
    
    # 1. .env 파일에서 누락된 필수 변수 확인
    missing_required = required_vars - set(env_vars.keys())
    if missing_required:
        issues.append(f"❌ .env 파일에 필수 환경 변수가 누락되었습니다: {', '.join(missing_required)}")
    
    # 2. .env.example 파일에서 누락된 변수 확인
    missing_in_example = (set(env_vars.keys()) - set(example_vars.keys())) - optional_vars
    if missing_in_example:
        issues.append(f"⚠️  .env.example 파일에 누락된 환경 변수: {', '.join(missing_in_example)}")
    
    # 3. 빈 값 확인 (필수 변수만)
    empty_required = []
    for var in required_vars:
        if var in env_vars and not env_vars[var]:
            empty_required.append(var)
        elif var in env_vars and env_vars[var] in ['your_', 'change_me', 'replace_this']:
            empty_required.append(var)
    
    if empty_required:
        issues.append(f"❌ .env 파일에 값이 비어있거나 기본값인 필수 변수: {', '.join(empty_required)}")
    
    # 4. 특정 값 검증
    validations = []
    
    # Alpha Vantage API 키 검증
    if 'ALPHA_VANTAGE_API_KEY' in env_vars:
        api_key = env_vars['ALPHA_VANTAGE_API_KEY']
        if api_key == 'your_alpha_vantage_api_key' or not api_key:
            validations.append("❌ ALPHA_VANTAGE_API_KEY가 기본값입니다. 실제 API 키로 변경해주세요.")
        elif len(api_key) < 16:
            validations.append("⚠️  ALPHA_VANTAGE_API_KEY가 너무 짧습니다. 올바른 API 키인지 확인해주세요.")
        else:
            validations.append("✅ ALPHA_VANTAGE_API_KEY가 설정되었습니다.")
    
    # Discord webhook URL 검증
    if 'DISCORD_WEBHOOK_URL' in env_vars:
        webhook_url = env_vars['DISCORD_WEBHOOK_URL']
        if 'discord.com/api/webhooks/' in webhook_url and len(webhook_url) > 80:
            validations.append("✅ Discord webhook URL이 올바르게 설정되었습니다.")
        else:
            validations.append("⚠️  Discord webhook URL 형식을 확인해주세요.")
    
    # 데이터베이스 설정 검증
    if all(var in env_vars for var in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER']):
        validations.append("✅ 데이터베이스 설정이 완료되었습니다.")
    
    # Redis 설정 검증
    if all(var in env_vars for var in ['REDIS_HOST', 'REDIS_PORT', 'REDIS_DB']):
        validations.append("✅ Redis 설정이 완료되었습니다.")
    
    # KIS API 설정 검증
    if all(var in env_vars for var in ['KIS_APP_KEY', 'KIS_APP_SECRET']):
        validations.append("✅ KIS API 설정이 완료되었습니다.")
    
    # 결과 출력
    print("\n" + "="*60)
    print("🔍 환경 변수 검증 결과")
    print("="*60)
    
    if validations:
        print("\n📊 설정 상태:")
        for validation in validations:
            print(f"   {validation}")
    
    if not issues:
        print("\n✅ 모든 환경 변수가 올바르게 설정되었습니다!")
        return True, []
    else:
        print("\n❌ 발견된 문제:")
        for issue in issues:
            print(f"   {issue}")
        return False, issues

def check_settings_integration():
    """settings.py 파일과의 통합 확인"""
    try:
        from app.config.settings import settings
        print("\n🔧 Settings 통합 확인:")
        
        # 주요 설정 확인
        config_checks = [
            ("데이터베이스", hasattr(settings, 'database_url')),
            ("Redis", hasattr(settings, 'redis_url')),
            ("KIS API", hasattr(settings, 'kis_app_key')),
            ("Alpha Vantage", hasattr(settings, 'alpha_vantage_api_key')),
            ("Discord", hasattr(settings, 'discord_webhook_url')),
        ]
        
        for name, check in config_checks:
            status = "✅" if check else "❌"
            print(f"   {status} {name} 설정")
        
        return True
    except Exception as e:
        print(f"\n❌ Settings 통합 확인 실패: {e}")
        return False

if __name__ == '__main__':
    print("🚀 환경 변수 검증을 시작합니다...")
    
    # 환경 변수 파일 검증
    is_valid, issues = validate_env_files()
    
    # Settings 통합 확인
    check_settings_integration()
    
    print("\n" + "="*60)
    
    if is_valid:
        print("🎉 환경 설정이 완료되었습니다! 프로덕션 배포가 가능합니다.")
        sys.exit(0)
    else:
        print("⚠️  환경 설정에 문제가 있습니다. 위의 문제들을 해결해주세요.")
        sys.exit(1)
