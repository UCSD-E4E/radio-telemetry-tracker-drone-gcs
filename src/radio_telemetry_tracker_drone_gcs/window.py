"""Main PyQt window with QWebEngineView to load the React/Leaflet frontend."""

import logging
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineScript
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Main application window that hosts the web-based frontend using QWebEngineView."""

    def __init__(self) -> None:
        """Initialize the main window and set up the web view with communication bridge."""
        super().__init__()
        self.setWindowTitle("Radio Telemetry Tracker Drone GCS")

        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)

        self.channel = QWebChannel()
        self.bridge = None
        self.web_view.page().setWebChannel(self.channel)

        # Dev tools
        self.web_view.page().setDevToolsPage(self.web_view.page())

        self.web_view.loadFinished.connect(self._on_load_finished)

        # Insert QWebChannel script
        script = QWebEngineScript()
        script.setName("qwebchannel")
        script.setSourceCode(
            """
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.backend = channel.objects.backend;
                window.backendLoaded = true;
                const event = new Event('backendLoaded');
                window.dispatchEvent(event);
            });
            """,
        )
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setRunsOnSubFrames(False)
        self.web_view.page().scripts().insert(script)

        self.resize(1280, 720)

        dist_path = Path(__file__).parent / "frontend_dist" / "index.html"
        if not dist_path.exists():
            logging.error("Frontend dist not found at %s", dist_path)
            msg = f"Frontend dist not found at {dist_path}"
            raise FileNotFoundError(msg)

        local_url = QUrl.fromLocalFile(str(dist_path))
        logging.info("Loading frontend from %s", local_url.toString())
        self.web_view.setUrl(local_url)

    def _on_load_finished(self, *, ok: bool = True) -> None:
        if ok:
            logging.info("Frontend loaded successfully")
        else:
            logging.error("Failed to load frontend")

    def set_bridge(self, bridge: object) -> None:
        """Register the communication bridge object with the web channel."""
        self.bridge = bridge
        self.channel.registerObject("backend", bridge)
        logging.info("Bridge registered with WebChannel")
