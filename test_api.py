#!/usr/bin/env python3
"""
Quick Test Script - Kiểm tra API Backend
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://34.87.54.108.nip.io"
# Hoặc local: BASE_URL = "http://localhost:5000"

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def test_health(self) -> bool:
        """Kiểm tra health endpoint"""
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=10)
            print(f"✅ Health Check: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health Check Failed: {e}")
            return False
    
    def test_register(self, username: str = "testuser") -> bool:
        """Kiểm tra endpoint đăng ký"""
        try:
            url = f"{self.base_url}/register"
            data = {
                "username": username,
                "email": f"{username}@test.com",
                "password": "Test@123456",
                "full_name": "Test User"
            }
            response = self.session.post(url, json=data, timeout=10)
            print(f"✅ Register: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code in [200, 400]  # 400 nếu user đã tồn tại
        except Exception as e:
            print(f"❌ Register Failed: {e}")
            return False
    
    def test_login(self, username: str = "testuser") -> bool:
        """Kiểm tra endpoint đăng nhập"""
        try:
            url = f"{self.base_url}/login"
            data = {
                "username": username,
                "password": "Test@123456"
            }
            response = self.session.post(url, data=data, timeout=10)
            print(f"✅ Login: {response.status_code}")
            result = response.json()
            print(f"   Response: {result}")
            
            if response.status_code == 200:
                self.token = result.get("access_token")
                return True
            return False
        except Exception as e:
            print(f"❌ Login Failed: {e}")
            return False
    
    def test_predict(self) -> bool:
        """Kiểm tra endpoint prediction"""
        try:
            url = f"{self.base_url}/predict"
            data = {
                "income": 5000000,
                "score": 750,
                "contact_status": "contacted"
            }
            
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            response = self.session.post(url, json=data, headers=headers, timeout=10)
            print(f"✅ Predict: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Predict Failed: {e}")
            return False
    
    def test_profile(self) -> bool:
        """Kiểm tra endpoint lấy profile"""
        if not self.token:
            print("⚠️ Profile: Bỏ qua (chưa đăng nhập)")
            return True
        
        try:
            url = f"{self.base_url}/profile"
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(url, headers=headers, timeout=10)
            print(f"✅ Profile: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Profile Failed: {e}")
            return False
    
    def test_metrics(self) -> bool:
        """Kiểm tra Prometheus metrics"""
        try:
            url = f"{self.base_url}/metrics"
            response = self.session.get(url, timeout=10)
            print(f"✅ Metrics: {response.status_code}")
            print(f"   Sample: {response.text[:200]}...")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Metrics Failed: {e}")
            return False
    
    def run_all_tests(self):
        """Chạy tất cả tests"""
        print("=" * 60)
        print(f"🚀 API Testing - Base URL: {self.base_url}")
        print("=" * 60)
        print()
        
        tests = [
            ("Health Check", self.test_health),
            ("Register", self.test_register),
            ("Login", self.test_login),
            ("Predict", self.test_predict),
            ("Profile", self.test_profile),
            ("Metrics", self.test_metrics)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n📝 Testing: {test_name}")
            results[test_name] = test_func()
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\n✅ Passed: {passed}/{total}")
        
        if passed == total:
            print("\n🎉 Tất cả tests đều passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Kiểm tra logs bên trên.")
            return 1

def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    tester = APITester(base_url)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
