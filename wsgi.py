import sys
import os

# Cesta k projektu
path = '/var/www/clients/client1/web9/private/project1'
if path not in sys.path:
    sys.path.append(path)

# Import Flask instance
from app import app as application

# Volitelné: pokud používáš v kódu relativní cesty, nastav pracovní adresář
os.chdir(path)
