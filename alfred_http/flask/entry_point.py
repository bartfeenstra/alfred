import importlib
import sys

from alfred.app import App
from alfred_http.extension import HttpExtension

alfred = App()
alfred.start()
alfred.add_extension(HttpExtension)
for qualname in sys.argv[1:]:
    module_name, class_name = qualname.rsplit('.', 1)
    importlib.import_module(module_name)
    module = sys.modules[module_name]
    extension = getattr(module, class_name)
    alfred.add_extension(extension)
app = alfred.service('http', 'flask')
