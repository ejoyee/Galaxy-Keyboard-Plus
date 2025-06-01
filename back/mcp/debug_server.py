#!/usr/bin/env python3
"""
FastAPI 서버 디버그 도구
airbnb_caching 엔드포인트가 등록되었는지 확인
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from app.main import app

def debug_routes():
    """등록된 모든 라우트 확인"""
    print("=== FastAPI 라우트 디버그 ===")
    print(f"앱 제목: {app.title}")
    print(f"문서 URL: {app.docs_url}")
    print(f"OpenAPI URL: {app.openapi_url}")
    print("\n등록된 라우트들:")
    
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"  {route.methods} {route.path}")
            if hasattr(route, 'name'):
                print(f"    함수명: {route.name}")
        
    print("\n=== airbnb_caching 관련 라우트 확인 ===")
    airbnb_routes = [route for route in app.routes 
                    if hasattr(route, 'path') and 'caching' in route.path]
    
    if airbnb_routes:
        print("✅ airbnb_caching 라우트 발견:")
        for route in airbnb_routes:
            print(f"  {route.methods} {route.path}")
    else:
        print("❌ airbnb_caching 라우트를 찾을 수 없습니다.")
    
    print("\n=== OpenAPI 스펙 확인 ===")
    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get('paths', {})
        
        caching_paths = {path: info for path, info in paths.items() 
                        if 'caching' in path}
        
        if caching_paths:
            print("✅ OpenAPI 스펙에 caching 엔드포인트 존재:")
            for path, info in caching_paths.items():
                print(f"  {path}: {list(info.keys())}")
        else:
            print("❌ OpenAPI 스펙에 caching 엔드포인트가 없습니다.")
            
        print(f"\n전체 경로 수: {len(paths)}")
        print("모든 경로:")
        for path in sorted(paths.keys()):
            print(f"  {path}")
            
    except Exception as e:
        print(f"❌ OpenAPI 스펙 생성 중 오류: {e}")

if __name__ == "__main__":
    debug_routes()
