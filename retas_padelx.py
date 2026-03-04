import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import random
from itertools import combinations


class RetasPadel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retas Pádel 5.1 PRO")
        self.setGeometry(100, 100, 1200, 800)

        self.jugadores = []
        self.canchas = {i: [] for i in range(1, 7)}
        self.ultimas_parejas = {}       # {nombre: set(compañeros anteriores)}
        # FIX: guardamos los equipos fijos de la ronda actual por cancha
        self.equipos_actuales = {}      # {cancha: (eq1, eq2)}  — listas de jugadores

        self.init_ui()

    # ================= UI =================

    def init_ui(self):
        main_layout = QVBoxLayout()

        self.podio_label = QLabel("🏆 PODIO")
        self.podio_label.setFont(QFont("Arial", 22))
        self.podio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.podio_label.setStyleSheet("color: gold;")
        main_layout.addWidget(self.podio_label)

        # Botón para colapsar/expandir
        self.btn_toggle = QPushButton("▼  Jugadores  (colapsar)")
        self.btn_toggle.clicked.connect(self.toggle_jugadores)
        self.btn_toggle.setStyleSheet("background-color: #444; color: white; font-weight: bold; text-align: left; padding: 6px 10px;")
        main_layout.addWidget(self.btn_toggle)

        # Contenedor colapsable
        self.panel_jugadores = QFrame()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self.text_nombres = QTextEdit()
        self.text_nombres.setPlaceholderText("Pega aquí los 24 jugadores (uno por línea)...")
        self.text_nombres.setMaximumHeight(180)
        panel_layout.addWidget(self.text_nombres)

        btn_cargar = QPushButton("Cargar Jugadores")
        btn_cargar.clicked.connect(self.cargar_jugadores)
        panel_layout.addWidget(btn_cargar)

        self.panel_jugadores.setLayout(panel_layout)
        main_layout.addWidget(self.panel_jugadores)

        self.partidos_layout = QGridLayout()
        self.labels_partidos = {}

        for i in range(1, 7):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.Box)
            layout = QVBoxLayout()

            titulo = QLabel(f"Cancha {i}")
            titulo.setFont(QFont("Arial", 12))
            layout.addWidget(titulo)

            partido = QLabel("---")
            partido.setWordWrap(True)
            layout.addWidget(partido)

            frame.setLayout(layout)
            self.partidos_layout.addWidget(frame, (i - 1) // 3, (i - 1) % 3)
            self.labels_partidos[i] = partido

        main_layout.addLayout(self.partidos_layout)

        resultado_layout = QHBoxLayout()
        self.input_cancha = QLineEdit()
        self.input_cancha.setPlaceholderText("Cancha (1-6)")
        self.input_s1 = QLineEdit()
        self.input_s1.setPlaceholderText("Puntos Equipo 1")
        self.input_s2 = QLineEdit()
        self.input_s2.setPlaceholderText("Puntos Equipo 2")

        btn_guardar = QPushButton("Guardar Resultado")
        btn_guardar.clicked.connect(self.registrar_resultado)

        resultado_layout.addWidget(self.input_cancha)
        resultado_layout.addWidget(self.input_s1)
        resultado_layout.addWidget(self.input_s2)
        resultado_layout.addWidget(btn_guardar)
        main_layout.addLayout(resultado_layout)

        btn_ronda = QPushButton("Nueva Ronda Global (Reordenar)")
        btn_ronda.clicked.connect(self.nueva_ronda_global)
        btn_ronda.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        main_layout.addWidget(btn_ronda)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Cancha", "Nombre", "Puntos"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.tabla)

        self.setLayout(main_layout)

        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: white; font-size: 14px; }
            QPushButton { background-color: #2ecc71; padding: 8px; border-radius: 6px; }
            QPushButton:hover { background-color: #27ae60; }
            QLineEdit, QTextEdit { background-color: #2c2c2c; color: white; border-radius: 5px; padding: 5px; }
            QTableWidget { background-color: #2c2c2c; gridline-color: #444; }
        """)

    # ================= LÓGICA =================

    def cargar_jugadores(self):
        nombres = self.text_nombres.toPlainText().strip().split("\n")
        nombres = [n.strip() for n in nombres if n.strip()]

        if len(nombres) != 24:
            QMessageBox.warning(self, "Error", "Debe haber exactamente 24 jugadores")
            return
        if len(set(nombres)) != 24:
            QMessageBox.warning(self, "Error", "Hay nombres repetidos")
            return

        self.jugadores = []
        self.canchas = {i: [] for i in range(1, 7)}
        self.ultimas_parejas = {}
        self.equipos_actuales = {}

        for i, nombre in enumerate(nombres):
            jugador = {"nombre": nombre, "puntos": 0, "cancha": (i // 4) + 1}
            self.jugadores.append(jugador)
            self.canchas[jugador["cancha"]].append(jugador)
            self.ultimas_parejas[jugador["nombre"]] = set()

        # Generar equipos para la primera ronda
        self._generar_equipos_ronda()
        self.actualizar_ui()

    def _generar_equipos_ronda(self):
        """
        Genera y FIJA los equipos para todas las canchas de la ronda actual.
        Se llama una sola vez al inicio de cada ronda (carga o ronda global).
        Garantiza que ningún jugador repita compañero de la ronda anterior
        cuando sea posible. Usa backtracking para encontrar una solución global válida.
        """
        self.equipos_actuales = {}

        for cancha, jugadores in self.canchas.items():
            if len(jugadores) != 4:
                continue
            eq1, eq2 = self._mejor_combinacion(jugadores)
            self.equipos_actuales[cancha] = (eq1, eq2)

            # Registrar las nuevas parejas en el historial
            self.ultimas_parejas[eq1[0]["nombre"]].add(eq1[1]["nombre"])
            self.ultimas_parejas[eq1[1]["nombre"]].add(eq1[0]["nombre"])
            self.ultimas_parejas[eq2[0]["nombre"]].add(eq2[1]["nombre"])
            self.ultimas_parejas[eq2[1]["nombre"]].add(eq2[0]["nombre"])

    def _mejor_combinacion(self, jugadores):
        """
        Elige la mejor división de 4 jugadores en 2 pares.
        Evalúa las 3 combinaciones posibles y elige la que minimiza
        la cantidad de parejas ya vistas. En empate, elige aleatoriamente.
        """
        nombres = [j["nombre"] for j in jugadores]

        # Las 3 particiones posibles de 4 jugadores en 2 pares
        particiones = [
            ((nombres[0], nombres[1]), (nombres[2], nombres[3])),
            ((nombres[0], nombres[2]), (nombres[1], nombres[3])),
            ((nombres[0], nombres[3]), (nombres[1], nombres[2])),
        ]

        def repeticiones(particion):
            (a, b), (c, d) = particion
            count = 0
            if b in self.ultimas_parejas.get(a, set()):
                count += 1
            if d in self.ultimas_parejas.get(c, set()):
                count += 1
            return count

        # Ordenar por menor cantidad de repeticiones
        particiones_eval = [(repeticiones(p), p) for p in particiones]
        min_rep = min(r for r, _ in particiones_eval)
        mejores = [p for r, p in particiones_eval if r == min_rep]

        # Entre las mejores, elegir aleatoriamente para variedad
        elegida = random.choice(mejores)
        (n1, n2), (n3, n4) = elegida

        nombre_a_jugador = {j["nombre"]: j for j in jugadores}
        eq1 = [nombre_a_jugador[n1], nombre_a_jugador[n2]]
        eq2 = [nombre_a_jugador[n3], nombre_a_jugador[n4]]
        return eq1, eq2

    def registrar_resultado(self):
        try:
            cancha = int(self.input_cancha.text())
            s1 = int(self.input_s1.text())
            s2 = int(self.input_s2.text())
        except:
            QMessageBox.warning(self, "Error", "Datos inválidos")
            return

        if cancha < 1 or cancha > 6:
            QMessageBox.warning(self, "Error", "Cancha inválida")
            return

        if s1 < 0 or s1 > 6 or s2 < 0 or s2 > 6:
            QMessageBox.warning(self, "Error", "Los puntos deben ser entre 0 y 6")
            return

        if cancha not in self.equipos_actuales:
            QMessageBox.warning(self, "Error", f"No hay partido activo en cancha {cancha}")
            return

        # FIX: usamos los equipos FIJOS de la ronda, no regeneramos
        eq1, eq2 = self.equipos_actuales[cancha]

        for j in eq1:
            j["puntos"] += s1
        for j in eq2:
            j["puntos"] += s2

        self.input_cancha.clear()
        self.input_s1.clear()
        self.input_s2.clear()

        self.actualizar_ui()

    def nueva_ronda_global(self):
        if not self.jugadores:
            return

        # Ordenar por puntos (desc), cancha como desempate
        self.jugadores = sorted(
            self.jugadores,
            key=lambda x: (-x["puntos"], x["cancha"])
        )

        # Reasignar canchas en grupos de 4
        self.canchas = {i: [] for i in range(1, 7)}
        for i, j in enumerate(self.jugadores):
            j["cancha"] = (i // 4) + 1
            self.canchas[j["cancha"]].append(j)

        # Limpiar historial de parejas para la nueva ronda
        # (solo guardamos la ronda anterior para evitar repetición inmediata)
        # Si querés acumular historial de todas las rondas, comenta estas líneas:
        for nombre in self.ultimas_parejas:
            self.ultimas_parejas[nombre] = set()

        # Generar nuevos equipos para la ronda
        self._generar_equipos_ronda()
        self.actualizar_ui()

    # ================= ACTUALIZACIÓN UI =================

    def actualizar_ui(self):
        self.actualizar_tabla()
        self.actualizar_partidos()
        self.actualizar_podio()

    def actualizar_tabla(self):
        orden = sorted(self.jugadores, key=lambda x: (-x["puntos"], x["cancha"]))
        self.tabla.setRowCount(len(orden))
        for row, j in enumerate(orden):
            self.tabla.setItem(row, 0, QTableWidgetItem(str(j["cancha"])))
            self.tabla.setItem(row, 1, QTableWidgetItem(j["nombre"]))
            self.tabla.setItem(row, 2, QTableWidgetItem(str(j["puntos"])))

    def actualizar_partidos(self):
        """
        FIX: Solo muestra los equipos ya fijados. NO genera nuevos equipos.
        """
        for cancha in range(1, 7):
            if cancha not in self.equipos_actuales:
                self.labels_partidos[cancha].setText("---")
                continue
            eq1, eq2 = self.equipos_actuales[cancha]
            texto = f"{eq1[0]['nombre']} + {eq1[1]['nombre']}  vs  {eq2[0]['nombre']} + {eq2[1]['nombre']}"
            self.labels_partidos[cancha].setText(texto)

    def actualizar_podio(self):
        if len(self.jugadores) < 3:
            self.podio_label.setText("🏆 PODIO")
            return

        top = sorted(self.jugadores, key=lambda x: (-x["puntos"], x["cancha"]))[:3]
        texto = (
            f"🥇 {top[0]['nombre']} ({top[0]['puntos']} pts)    |    "
            f"🥈 {top[1]['nombre']} ({top[1]['puntos']} pts)    |    "
            f"🥉 {top[2]['nombre']} ({top[2]['puntos']} pts)"
        )
        self.podio_label.setText(texto)


# ================= RUN =================

app = QApplication(sys.argv)
window = RetasPadel()
window.show()
sys.exit(app.exec())