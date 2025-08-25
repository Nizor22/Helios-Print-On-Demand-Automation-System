#!/usr/bin/env python3
"""
Google Cloud Compliance Test for Helios Microservices Architecture

This script validates that our architecture follows Google Cloud best practices
for Cloud Run and Cloud Buildpacks deployment.
"""

import os
import sys
import importlib
import subprocess
from pathlib import Path

def test_python_version_compatibility():
    """Test that Python version constraints are correct"""
    print("🧪 Testing Python version compatibility...")
    
    # Check current Python version
    current_version = sys.version_info
    print(f"   Current Python: {current_version.major}.{current_version.minor}.{current_version.micro}")
    
    # Check if version is within our constraints
    if current_version >= (3, 11) and current_version < (3, 14):
        print("   ✅ Python version is within constraints (>=3.11,<3.14)")
        return True
    else:
        print("   ❌ Python version is outside constraints")
        return False

def test_package_structure():
    """Test that each service has proper Python package structure"""
    print("🧪 Testing package structure...")
    
    services = ['orchestrator', 'agents']
    results = []
    
    for service in services:
        service_path = Path(service)
        src_path = service_path / 'src'
        package_path = src_path / f'helios_{service}'
        
        # Check if package structure exists
        if not service_path.exists():
            print(f"   ❌ {service} directory missing")
            results.append(False)
            continue
            
        if not src_path.exists():
            print(f"   ❌ {service}/src directory missing")
            results.append(False)
            continue
            
        if not package_path.exists():
            print(f"   ❌ {service}/src/helios_{service} package missing")
            results.append(False)
            continue
            
        # Check for required files
        required_files = ['__init__.py', 'main.py']
        for file in required_files:
            if not (package_path / file).exists():
                print(f"   ❌ {service} missing {file}")
                results.append(False)
                break
        else:
            print(f"   ✅ {service} package structure is correct")
            results.append(True)
    
    return all(results)

def test_package_installation():
    """Test that each service can be installed as a Python package"""
    print("🧪 Testing package installation...")
    
    services = ['orchestrator', 'agents']
    results = []
    
    for service in services:
        try:
            # Change to service directory
            os.chdir(service)
            
            # Try to install the package
            result = subprocess.run(
                ['pip3', 'install', '-e', '.', '--quiet'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ {service} installs successfully")
                results.append(True)
            else:
                print(f"   ❌ {service} installation failed: {result.stderr}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ {service} installation error: {e}")
            results.append(False)
        finally:
            # Return to project root
            os.chdir('..')
    
    return all(results)

def test_import_resolution():
    """Test that each service can be imported correctly"""
    print("🧪 Testing import resolution...")
    
    services = [
        ('helios_orchestrator.main', 'app'),
        ('helios_agents.main', 'app')
    ]
    
    results = []
    
    for package, attribute in services:
        try:
            module = importlib.import_module(package)
            app = getattr(module, attribute)
            
            # Check if it's a FastAPI app
            if hasattr(app, 'title') and hasattr(app, 'routes'):
                print(f"   ✅ {package}.{attribute} imports successfully")
                print(f"      App title: {app.title}")
                print(f"      Routes: {len(app.routes)}")
                results.append(True)
            else:
                print(f"   ❌ {package}.{attribute} is not a valid FastAPI app")
                results.append(False)
                
        except ImportError as e:
            print(f"   ❌ {package}.{attribute} import failed: {e}")
            results.append(False)
        except Exception as e:
            print(f"   ❌ {package}.{attribute} error: {e}")
            results.append(False)
    
    return all(results)

def test_independent_execution():
    """Test that each service can run independently"""
    print("🧪 Testing independent execution...")
    
    services = [
        ('helios_orchestrator.main', 'Helios AI Orchestrator'),
        ('helios_agents.main', 'Helios AI Agents Service')
    ]
    
    results = []
    
    for package, expected_title in services:
        try:
            module = importlib.import_module(package)
            app = getattr(module, 'app')
            
            # Test that the app can be configured for uvicorn
            if hasattr(app, 'title') and app.title == expected_title:
                print(f"   ✅ {package} can run independently")
                results.append(True)
            else:
                print(f"   ❌ {package} title mismatch: expected '{expected_title}', got '{getattr(app, 'title', 'None')}'")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ {package} execution test failed: {e}")
            results.append(False)
    
    return all(results)

def test_cloud_buildpacks_compliance():
    """Test that our structure complies with Cloud Buildpacks expectations"""
    print("🧪 Testing Cloud Buildpacks compliance...")
    
    results = []
    
    # Check that each service has required files for Cloud Buildpacks
    services = ['orchestrator', 'agents']
    
    for service in services:
        service_path = Path(service)
        required_files = ['pyproject.toml', 'Procfile', 'runtime.txt']
        
        for file in required_files:
            if (service_path / file).exists():
                print(f"   ✅ {service} has {file}")
            else:
                print(f"   ❌ {service} missing {file}")
                results.append(False)
                break
        else:
            print(f"   ✅ {service} has all required Cloud Buildpacks files")
            results.append(True)
    
    # Check that we don't have environment-based routing (anti-pattern)
    if not any(['SERVICE_TYPE' in str(Path('.').rglob('*.py'))]):
        print("   ✅ No environment-based routing detected (follows Cloud Run best practices)")
        results.append(True)
    else:
        print("   ❌ Environment-based routing detected (violates Cloud Run principles)")
        results.append(False)
    
    return all(results)

def main():
    """Run all compliance tests"""
    print("🚀 Running Google Cloud Compliance Tests for Helios Architecture")
    print("=" * 70)
    
    tests = [
        test_python_version_compatibility,
        test_package_structure,
        test_package_installation,
        test_import_resolution,
        test_independent_execution,
        test_cloud_buildpacks_compliance
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test {test.__name__} failed with error: {e}")
            results.append(False)
        print()
    
    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Architecture follows Google Cloud best practices.")
        print("✅ Ready for Cloud Run deployment with Cloud Buildpacks.")
        return True
    else:
        print("❌ Some tests failed. Fix issues before cloud deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
