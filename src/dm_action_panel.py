from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSpinBox,
    QPushButton,
)

class DMActionPanel(QWidget):
    """A compact widget that groups together the DM-assistance controls.

    The panel contains:
    • Two parameter spin-boxes (PC Level & Quantity)
    • Eight action buttons arranged in a 2×4 grid

    External code can access the public attributes (spin-boxes & buttons)
    to connect signals/slots.  A convenience :py:meth:`set_controls_enabled`
    method toggles the enabled state of every interactive child at once.
    """

    def __init__(self, initial_pc_level: int = 1, initial_quantity: int = 1, parent: QWidget | None = None):
        super().__init__(parent)

        # ---------- Layout skeleton ----------
        root_layout = QVBoxLayout(self)
        self.setLayout(root_layout)

        # Parameter row (horizontal)
        param_layout = QHBoxLayout()
        root_layout.addLayout(param_layout)

        # PC Level
        self.pc_level_label = QLabel("PC Level:")
        self.pc_level_spinbox = QSpinBox()
        self.pc_level_spinbox.setRange(1, 20)
        self.pc_level_spinbox.setValue(initial_pc_level)
        param_layout.addWidget(self.pc_level_label)
        param_layout.addWidget(self.pc_level_spinbox)

        # Quantity
        self.quantity_label = QLabel("Quantity:")
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setRange(1, 10)
        self.quantity_spinbox.setValue(initial_quantity)
        param_layout.addWidget(self.quantity_label)
        param_layout.addWidget(self.quantity_spinbox)

        param_layout.addStretch(1)  # push widgets to left, fill width

        # Action buttons grid (2 rows × 4 columns)
        grid_layout = QGridLayout()
        root_layout.addLayout(grid_layout)

        # Row 0
        self.generate_npc_button = QPushButton("Gen NPC")
        self.describe_surroundings_button = QPushButton("Describe Env")
        self.generate_encounter_button = QPushButton("Gen Encounter")
        self.suggest_rumor_button = QPushButton("Suggest Rumor")

        grid_layout.addWidget(self.generate_npc_button, 0, 0)
        grid_layout.addWidget(self.describe_surroundings_button, 0, 1)
        grid_layout.addWidget(self.generate_encounter_button, 0, 2)
        grid_layout.addWidget(self.suggest_rumor_button, 0, 3)

        # Row 1
        self.suggest_complication_button = QPushButton("Suggest Twist")
        self.generate_mundane_items_button = QPushButton("Gen Mundane")
        self.generate_loot_button = QPushButton("Gen Loot")
        self.test_button = QPushButton("Test Action")

        grid_layout.addWidget(self.suggest_complication_button, 1, 0)
        grid_layout.addWidget(self.generate_mundane_items_button, 1, 1)
        grid_layout.addWidget(self.generate_loot_button, 1, 2)
        grid_layout.addWidget(self.test_button, 1, 3)

        # Stretch last column to occupy remaining space so the grid spans the
        # width of the right-hand log pane (parent layouts can still control).
        for col in range(4):
            grid_layout.setColumnStretch(col, 1)

    # ---------------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------------
    def set_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable every interactive child control in the panel."""
        for widget in (
            self.pc_level_spinbox,
            self.quantity_spinbox,
            self.generate_npc_button,
            self.describe_surroundings_button,
            self.generate_encounter_button,
            self.suggest_rumor_button,
            self.suggest_complication_button,
            self.generate_mundane_items_button,
            self.generate_loot_button,
            self.test_button,
        ):
            widget.setEnabled(enabled) 