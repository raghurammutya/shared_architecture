import subprocess
import sys

def run_pytest():
    result = subprocess.run(["pytest", "tests/", "-v", "--tb=short"], check=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    run_pytest()
