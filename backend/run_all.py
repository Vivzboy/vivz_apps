#!/usr/bin/env python3
"""
Cape Town Property App - All-in-One Launcher 🚀
Handles MongoDB, Backend API, and optionally Frontend
"""

import subprocess
import time
import os
import sys
import signal
import platform
import psutil
import socket

class Colors:
    """Terminal colors for pretty output"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED
    }
    color = colors.get(status, Colors.BLUE)
    print(f"{color}{Colors.BOLD}{message}{Colors.ENDC}")

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """Kill process using a specific port"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        print_status(f"Killing {proc.info['name']} (PID: {proc.info['pid']}) on port {port}", "warning")
                        proc.terminate()
                        time.sleep(1)
                        if proc.is_running():
                            proc.kill()
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print_status(f"Error killing process on port {port}: {e}", "error")
    return False

def check_mongodb_installed():
    """Check if MongoDB is installed"""
    try:
        subprocess.run(["mongod", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_mongodb():
    """Start MongoDB with proper error handling"""
    MONGODB_PORT = 27018  # Using custom port to avoid conflicts
    print_status(f"🗄️  Starting MongoDB on port {MONGODB_PORT}...", "info")
    
    # Check if MongoDB is installed
    if not check_mongodb_installed():
        print_status("MongoDB not found! Please install it first:", "error")
        print("  brew install mongodb-community  # Mac")
        print("  sudo apt install mongodb        # Ubuntu/Debian")
        return None
    
    # Check if MongoDB is already running on our custom port
    if is_port_in_use(MONGODB_PORT):
        print_status(f"MongoDB is already running on port {MONGODB_PORT}", "warning")
        response = input("Kill existing MongoDB process? (y/n): ")
        if response.lower() == 'y':
            kill_process_on_port(MONGODB_PORT)
            time.sleep(2)
        else:
            print_status("Using existing MongoDB instance", "success")
            return None
    
    # Create data directory if it doesn't exist
    data_dir = "/data/db"
    if platform.system() == "Darwin":  # macOS
        data_dir = os.path.expanduser("~/data/db")
    
    if not os.path.exists(data_dir):
        print_status(f"Creating MongoDB data directory: {data_dir}", "info")
        os.makedirs(data_dir, exist_ok=True)
    
    # Start MongoDB
    try:
        if platform.system() == "Darwin":  # macOS
            process = subprocess.Popen(
                ["mongod", "--dbpath", data_dir, "--port", str(MONGODB_PORT), "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            process = subprocess.Popen(
                ["mongod", "--port", str(MONGODB_PORT), "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        # Wait a bit and check if it started
        time.sleep(3)
        if process.poll() is None:
            print_status("✅ MongoDB started successfully", "success")
            return process
        else:
            print_status("❌ MongoDB failed to start", "error")
            stderr = process.stderr.read().decode()
            print(stderr)
            return None
            
    except Exception as e:
        print_status(f"❌ Failed to start MongoDB: {e}", "error")
        return None

def start_backend():
    """Start the FastAPI backend"""
    print_status("🚀 Starting Backend API...", "info")
    
    # Check if backend port is in use
    if is_port_in_use(8000):
        print_status("Port 8000 is already in use", "warning")
        response = input("Kill existing process on port 8000? (y/n): ")
        if response.lower() == 'y':
            kill_process_on_port(8000)
            time.sleep(2)
        else:
            return None
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    if not os.path.exists(backend_dir):
        backend_dir = "."  # Already in backend directory
    
    # Check if main.py exists
    main_py = os.path.join(backend_dir, "main.py")
    if not os.path.exists(main_py):
        print_status("❌ main.py not found! Are you in the right directory?", "error")
        return None
    
    # Create .env file if it doesn't exist
    env_file = os.path.join(backend_dir, ".env")
    if not os.path.exists(env_file):
        print_status("📝 Creating .env file with custom MongoDB port...", "info")
        with open(env_file, 'w') as f:
            f.write("# Cape Town Property App Configuration\n")
            f.write("MONGODB_URL=mongodb://localhost:27018\n")
            f.write("DATABASE_NAME=cape_town_properties\n")
    
    # Install requirements if needed
    requirements_file = os.path.join(backend_dir, "requirements.txt")
    if os.path.exists(requirements_file):
        print_status("📦 Installing Python dependencies...", "info")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], 
                      capture_output=True)
    
    # Set environment variables
    env = os.environ.copy()
    env["MONGODB_URL"] = "mongodb://localhost:27018"
    env["DATABASE_NAME"] = "cape_town_properties"
    
    # Start the backend
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup
        time.sleep(5)
        
        if process.poll() is None:
            print_status("✅ Backend API started successfully", "success")
            print_status("   📚 API Docs: http://localhost:8000/docs", "info")
            print_status("   🏥 Health: http://localhost:8000/health", "info")
            return process
        else:
            print_status("❌ Backend failed to start", "error")
            stderr = process.stderr.read().decode()
            print(stderr)
            return None
            
    except Exception as e:
        print_status(f"❌ Failed to start backend: {e}", "error")
        return None

def start_frontend():
    """Start the React frontend (optional)"""
    print_status("🎨 Starting Frontend...", "info")
    
    # Check if frontend port is in use
    if is_port_in_use(5173):
        print_status("Port 5173 is already in use (frontend probably running)", "warning")
        return None
    
    # Find frontend directory
    possible_dirs = [".", "src", "../src", "../", "frontend", "../frontend"]
    frontend_dir = None
    
    for dir_path in possible_dirs:
        package_json = os.path.join(dir_path, "package.json")
        if os.path.exists(package_json):
            frontend_dir = dir_path
            break
    
    if not frontend_dir:
        print_status("⚠️  Frontend directory not found (package.json missing)", "warning")
        print_status("   You can start it manually with: npm run dev", "info")
        return None
    
    # Install dependencies if needed
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print_status("📦 Installing frontend dependencies...", "info")
        subprocess.run(["npm", "install"], cwd=frontend_dir, capture_output=True)
    
    # Start frontend
    try:
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(5)
        
        if process.poll() is None:
            print_status("✅ Frontend started successfully", "success")
            print_status("   🌐 App URL: http://localhost:5173", "info")
            return process
        else:
            print_status("❌ Frontend failed to start", "error")
            return None
            
    except Exception as e:
        print_status(f"⚠️  Frontend start skipped: {e}", "warning")
        return None

def health_check():
    """Check if backend is healthy"""
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("✅ Backend health check passed", "success")
            if data.get("database", {}).get("status") == "healthy":
                print_status("✅ Database connection healthy", "success")
            return True
    except:
        pass
    return False

def create_sample_data():
    """Optional: Create sample data"""
    import requests
    
    print_status("📝 Creating sample properties...", "info")
    
    sample_properties = [
        {
            "title": "Stunning Sea Point Apartment",
            "area": "Sea Point",
            "price": 1850000,
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqm": 95,
            "property_type": "Apartment",
            "highlights": ["Ocean views", "Modern kitchen", "24h security"],
            "neighborhood_vibe": "Vibrant beachfront living"
        },
        {
            "title": "Modern Camps Bay Villa",
            "area": "Camps Bay",
            "price": 8500000,
            "bedrooms": 4,
            "bathrooms": 3,
            "size_sqm": 280,
            "property_type": "House",
            "highlights": ["Pool", "Mountain views", "Entertainment area"],
            "neighborhood_vibe": "Exclusive beach paradise"
        }
    ]
    
    try:
        response = requests.post(
            "http://localhost:8000/api/scraper/import",
            json=sample_properties
        )
        if response.status_code == 200:
            result = response.json()
            print_status(f"✅ Created {result['processed']} sample properties", "success")
    except Exception as e:
        print_status(f"⚠️  Could not create sample data: {e}", "warning")

def main():
    """Main launcher function"""
    print_status("🏠 Cape Town Property App Launcher", "info")
    print_status("=" * 50, "info")
    
    processes = []
    
    # Parse arguments
    run_frontend = "--with-frontend" in sys.argv or "-f" in sys.argv
    create_samples = "--with-samples" in sys.argv or "-s" in sys.argv
    
    try:
        # Start MongoDB
        mongo_process = start_mongodb()
        if mongo_process:
            processes.append(mongo_process)
        
        # Start Backend
        backend_process = start_backend()
        if backend_process:
            processes.append(backend_process)
        else:
            print_status("❌ Backend failed to start, exiting...", "error")
            for p in processes:
                p.terminate()
            sys.exit(1)
        
        # Wait for backend to be ready
        print_status("⏳ Waiting for backend to initialize...", "info")
        time.sleep(3)
        
        # Health check
        if health_check():
            print_status("🎉 Backend is ready!", "success")
            
            # Create sample data if requested
            if create_samples:
                create_sample_data()
        else:
            print_status("⚠️  Backend health check failed", "warning")
        
        # Start Frontend if requested
        if run_frontend:
            frontend_process = start_frontend()
            if frontend_process:
                processes.append(frontend_process)
        
        # Summary
        print_status("\n" + "=" * 50, "info")
        print_status("🎉 Cape Town Property App is running!", "success")
        print_status("\n📍 Access Points:", "info")
        print_status("   Backend API: http://localhost:8000", "info")
        print_status("   API Docs: http://localhost:8000/docs", "info")
        print_status("   Health Check: http://localhost:8000/health", "info")
        
        if run_frontend:
            print_status("   Frontend App: http://localhost:5173", "info")
        else:
            print_status("\n💡 To start frontend separately:", "info")
            print_status("   npm run dev", "info")
        
        print_status("\n🛑 Press Ctrl+C to stop all services", "warning")
        
        # Keep running and handle shutdown
        while True:
            time.sleep(1)
            # Check if any process died
            for p in processes:
                if p and p.poll() is not None:
                    print_status(f"\n⚠️  A process died unexpectedly", "error")
                    raise KeyboardInterrupt
            
    except KeyboardInterrupt:
        print_status("\n\n🛑 Shutting down...", "warning")
        
        # Terminate all processes
        for process in processes:
            if process and process.poll() is None:
                process.terminate()
                
        # Give them time to shutdown gracefully
        time.sleep(2)
        
        # Force kill if still running
        for process in processes:
            if process and process.poll() is None:
                process.kill()
        
        print_status("✅ All services stopped", "success")
        print_status("👋 Goodbye!", "info")

if __name__ == "__main__":
    # Show usage
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python run_all.py [options]")
        print("\nOptions:")
        print("  -f, --with-frontend    Also start the React frontend")
        print("  -s, --with-samples     Create sample data after startup")
        print("  -h, --help            Show this help message")
        print("\nExamples:")
        print("  python run_all.py                    # Start MongoDB + Backend only")
        print("  python run_all.py -f                 # Start everything")
        print("  python run_all.py -f -s              # Start everything + sample data")
        sys.exit(0)
    
    main()
    