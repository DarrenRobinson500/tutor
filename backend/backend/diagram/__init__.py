import pkgutil
import importlib

# Registry: { "Clock": module, "Rect": module, ... }
DIAGRAM_REGISTRY = {}

for module_info in pkgutil.iter_modules(__path__):
    if module_info.name == "engine" or module_info.name.startswith("test_"):
        continue  # don't load engine or test files as diagram types

    module = importlib.import_module(f"{__name__}.{module_info.name}")
    # print("loading module:", module_info.name, hasattr(module, "DIAGRAM_TYPE"), hasattr(module, "parse"), hasattr(module, "render"))

    if hasattr(module, "DIAGRAM_TYPE") and hasattr(module, "parse") and hasattr(module, "render"):
        DIAGRAM_REGISTRY[module.DIAGRAM_TYPE] = module