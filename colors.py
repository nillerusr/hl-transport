RED='\033[01;31m'
GREEN='\033[01;32m'
YELLOW='\033[01;33m'
BLUE='\033[01;34m'
VIOLET='\033[01;35m'
LIGHT_BLUE='\033[01;36m'
WHITE='\033[01;37m'
VOID='\033[0m'


#color print
def print_c(msg, end='\n'):
	print(msg+VOID, end=end)
