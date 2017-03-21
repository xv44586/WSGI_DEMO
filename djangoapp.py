import sys
sys.path.insert(0, './helloworld')
from demo import wsgi


app = wsgi.application