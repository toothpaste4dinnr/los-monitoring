import streamlit.cli as stcli
import sys
import os

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "src/app.py"]
    sys.exit(stcli.main())
