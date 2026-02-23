"""
First-launch Terms & Conditions / Privacy Policy dialog.

Shown before the application starts if the user has not yet accepted.
Also accessible from Settings > About > "View Terms & Privacy Policy".
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTextBrowser, QWidget,
    QCheckBox, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.logger import get_logger
from utils.paths import get_assets_dir

logger = get_logger(__name__)


class TermsDialog(QDialog):
    """
    Modal dialog asking the user to accept Terms & Privacy Policy.

    The "I Accept" button is disabled until the user ticks the checkbox.
    Returns ``QDialog.DialogCode.Accepted`` on accept, ``Rejected`` on
    decline / close.
    """

    def __init__(self, parent=None, *, read_only: bool = False):
        """
        Parameters
        ----------
        read_only : bool
            If True, show terms for viewing only (no accept/decline buttons).
            Used when re-viewing from Settings.
        """
        super().__init__(parent)
        self.read_only = read_only
        self.setWindowTitle("NexRemote — Terms & Privacy Policy")
        self.setMinimumSize(700, 550)
        self.setup_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QLabel("Welcome to NexRemote")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel(
            "Please review and accept the Terms of Service and Privacy Policy to continue."
            if not self.read_only
            else "Terms of Service and Privacy Policy"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._make_text_tab("TERMS.md"), "Terms of Service")
        tabs.addTab(self._make_text_tab("PRIVACY.md"), "Privacy Policy")
        layout.addWidget(tabs, stretch=1)

        if self.read_only:
            # Close button only
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_row.addWidget(close_btn)
            layout.addLayout(btn_row)
        else:
            # Acceptance checkbox
            self.check = QCheckBox(
                "I have read and agree to the Terms of Service and Privacy Policy"
            )
            self.check.stateChanged.connect(self._on_check_changed)
            layout.addWidget(self.check)

            # Buttons
            btn_row = QHBoxLayout()
            btn_row.addStretch()

            decline_btn = QPushButton("Decline && Exit")
            decline_btn.clicked.connect(self.reject)
            btn_row.addWidget(decline_btn)

            self.accept_btn = QPushButton("I Accept")
            self.accept_btn.setEnabled(False)
            self.accept_btn.setDefault(True)
            self.accept_btn.clicked.connect(self.accept)
            btn_row.addWidget(self.accept_btn)

            layout.addLayout(btn_row)

    def _make_text_tab(self, filename: str) -> QWidget:
        """Load a markdown file from ``assets/legal/`` into a QTextBrowser."""
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        legal_dir = get_assets_dir() / "legal"
        md_path = legal_dir / filename
        if md_path.exists():
            text = md_path.read_text(encoding="utf-8")
            browser.setMarkdown(text)
        else:
            browser.setPlainText(f"[{filename} not found at {md_path}]")
            logger.warning(f"Legal document not found: {md_path}")

        return browser

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_check_changed(self, state):
        self.accept_btn.setEnabled(state == Qt.CheckState.Checked.value)
