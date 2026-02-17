import sys
from pathlib import Path

# Add src to path so we can import app_factory
sys.path.append(str(Path(__file__).parent.parent / "src"))

from software_factory_poc.api.app_factory import create_app
from software_factory_poc.configuration.main_settings import Settings


def show_routes():
    settings = Settings()
    app = create_app(settings)

    print(f"{'METHOD':<10} {'PATH':<50} {'NAME':<30}")
    print("-" * 90)

    for route in app.routes:
        if hasattr(route, "methods"):
            # API Route
            methods = ", ".join(route.methods)
            print(f"{methods:<10} {route.path:<50} {route.name:<30}")
        else:
            # Mounts or others
            print(f"{'MOUNT':<10} {route.path:<50} {route.name:<30}")


if __name__ == "__main__":
    show_routes()
