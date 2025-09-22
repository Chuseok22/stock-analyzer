#!/usr/bin/env python3
"""
프로덕션 배포를 위한 환경 변수 최종 점검 스크립트
"""

import os
import secrets
import string
from pathlib import Path

def generate_secure_key(length: int = 64) -> str:
    """안전한 랜덤 키 생성"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    env_file = Path('.env')
    
    print("🔒 프로덕션 배포 보안 체크리스트")
    print("=" * 50)
    
    # .env 파일 읽기
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # 보안 체크 항목들
    security_checks = []
    
    # 1. Alpha Vantage API 키 체크
    alpha_key = env_vars.get('ALPHA_VANTAGE_API_KEY', '')
    if alpha_key == 'your_alpha_vantage_api_key' or not alpha_key:
        security_checks.append({
            'status': '❌',
            'item': 'Alpha Vantage API Key',
            'issue': '기본값이거나 비어있음',
            'action': 'https://www.alphavantage.co/support/#api-key 에서 무료 API 키 발급'
        })
    else:
        security_checks.append({
            'status': '✅',
            'item': 'Alpha Vantage API Key',
            'issue': '설정됨',
            'action': '없음'
        })
    
    # 2. 보안 키들 체크
    secret_keys = ['SECRET_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY']
    for key_name in secret_keys:
        key_value = env_vars.get(key_name, '')
        if key_value in ['your_secret_key_here', 'your_jwt_secret_key_here', 'your_encryption_key_here', '']:
            security_checks.append({
                'status': '❌',
                'item': key_name,
                'issue': '기본값이거나 비어있음',
                'action': '강력한 랜덤 키로 교체 필요'
            })
            # 안전한 키 생성 제안
            new_key = generate_secure_key()
            print(f"\n🔑 제안하는 {key_name}: {new_key}")
        else:
            security_checks.append({
                'status': '✅',
                'item': key_name,
                'issue': '설정됨',
                'action': '없음'
            })
    
    # 3. 데이터베이스 보안 체크
    db_password = env_vars.get('DB_PASSWORD', '')
    if len(db_password) < 8:
        security_checks.append({
            'status': '⚠️',
            'item': 'Database Password',
            'issue': '패스워드가 너무 짧음',
            'action': '8자 이상의 강력한 패스워드 사용 권장'
        })
    else:
        security_checks.append({
            'status': '✅',
            'item': 'Database Password',
            'issue': '적절한 길이',
            'action': '없음'
        })
    
    # 4. Redis 보안 체크
    redis_password = env_vars.get('REDIS_PASSWORD', '')
    if not redis_password:
        security_checks.append({
            'status': '⚠️',
            'item': 'Redis Password',
            'issue': '패스워드가 설정되지 않음',
            'action': 'Redis 인증 활성화 권장'
        })
    else:
        security_checks.append({
            'status': '✅',
            'item': 'Redis Password',
            'issue': '설정됨',
            'action': '없음'
        })
    
    # 5. 프로덕션 설정 체크
    debug_mode = env_vars.get('DEBUG', '').lower()
    if debug_mode in ['true', '1', 'yes']:
        security_checks.append({
            'status': '❌',
            'item': 'Debug Mode',
            'issue': '프로덕션에서 DEBUG=true',
            'action': 'DEBUG=false로 변경'
        })
    else:
        security_checks.append({
            'status': '✅',
            'item': 'Debug Mode',
            'issue': 'DEBUG=false',
            'action': '없음'
        })
    
    # 결과 출력
    print("\n📋 보안 체크 결과:")
    critical_issues = 0
    warnings = 0
    
    for check in security_checks:
        print(f"{check['status']} {check['item']}: {check['issue']}")
        if check['action'] != '없음':
            print(f"   → 조치 필요: {check['action']}")
        
        if check['status'] == '❌':
            critical_issues += 1
        elif check['status'] == '⚠️':
            warnings += 1
    
    print(f"\n📊 요약:")
    print(f"   ❌ 심각한 문제: {critical_issues}개")
    print(f"   ⚠️  경고: {warnings}개")
    print(f"   ✅ 정상: {len(security_checks) - critical_issues - warnings}개")
    
    # GitHub Secrets용 환경 변수 목록 생성
    print(f"\n📝 GitHub Secrets 설정용 환경 변수 목록:")
    print("=" * 50)
    
    important_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_BASE_URL',
        'ALPHA_VANTAGE_API_KEY',
        'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB',
        'DISCORD_ENABLED', 'DISCORD_WEBHOOK_URL',
        'SECRET_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY'
    ]
    
    for var in important_vars:
        value = env_vars.get(var, 'NOT_SET')
        # 민감한 정보는 일부만 표시
        if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
            if len(value) > 10:
                display_value = value[:5] + "..." + value[-3:]
            else:
                display_value = "***"
        else:
            display_value = value
        
        print(f"{var}={display_value}")
    
    if critical_issues > 0:
        print(f"\n❌ {critical_issues}개의 심각한 보안 문제가 발견되었습니다.")
        print("   프로덕션 배포 전에 반드시 해결해주세요!")
        return False
    elif warnings > 0:
        print(f"\n⚠️  {warnings}개의 경고가 있습니다.")
        print("   가능하면 배포 전에 개선해주세요.")
        return True
    else:
        print("\n🎉 모든 보안 체크를 통과했습니다!")
        print("   프로덕션 배포 준비가 완료되었습니다.")
        return True

if __name__ == '__main__':
    main()
