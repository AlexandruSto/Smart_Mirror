import subprocess
import time
import webbrowser

def run_python_file(filename):
    # Run the Python file in a separate process
    subprocess.Popen(['python', filename])

if _name_ == '_main_':
    # File to run
    python_file = 'homepage.py'

    # Run the Python file
    run_python_file(python_file)

    # Wait for 2 seconds
    time.sleep(2)

    # Open the webpage
    url = 'http://127.0.0.1:8000'
    webbrowser.open(url)
