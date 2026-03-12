import os
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
import tempfile

from PyQt5.QtCore import QTimer, Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QCheckBox,
                             QTimeEdit, QListWidget, QFileDialog,
                             QSystemTrayIcon, QMenu, QMessageBox, QScrollArea,
                             QGroupBox, QListWidgetItem, QStyle)


class RuleWidget(QWidget):
    def __init__(self, rule_data, on_remove, on_edit):
        super().__init__()
        self.rule_data = rule_data
        self.on_remove = on_remove
        self.on_edit = on_edit
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Informações da regra
        self.info_label = QLabel(self.format_rule_info())
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { padding: 5px; }")
        layout.addWidget(self.info_label, 1)
        
        # Botões
        buttons_layout = QVBoxLayout()
        
        edit_btn = QPushButton("Editar")
        edit_btn.setFixedSize(50, 25)
        edit_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 3px; font-size: 10px; }")
        edit_btn.clicked.connect(self.edit_rule)
        
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(25, 25)
        remove_btn.setStyleSheet("QPushButton { background-color: #ff4444; color: white; border: none; border-radius: 3px; font-size: 12px; }")
        remove_btn.clicked.connect(self.remove_rule)
        
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(remove_btn)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("QWidget { border: 1px solid #cccccc; border-radius: 5px; margin: 2px; }")

    def format_rule_info(self):
        days_pt = {
            "Mon": "Segunda", "Tue": "Terça", "Wed": "Quarta",
            "Thu": "Quinta", "Fri": "Sexta", "Sat": "Sábado", "Sun": "Domingo"
        }
        days_str = ", ".join([days_pt[day] for day in self.rule_data["days"]])
        folder_name = os.path.basename(self.rule_data['folder'])
        if len(folder_name) > 20:
            folder_name = folder_name[:17] + "..."
        return f"Pasta: {folder_name}\nHorário: {self.rule_data['time']} | Dias: {days_str}"

    def remove_rule(self):
        self.on_remove(self.rule_data)
        
    def edit_rule(self):
        self.on_edit(self.rule_data)
        
    def update_display(self):
        """Atualiza a exibição da regra"""
        self.info_label.setText(self.format_rule_info())


class FileCleanerApp(QMainWindow):
    # Sinal para atualização thread-safe da UI
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.tray_icon = None
        self.config_file = "config.json"
        self.log_file = "log.txt"
        self.config = self.load_config()
        self.active_mode = self.config.get("active", False)
        self.execution_history = {}
        self.editing_rule = None  # Regra atualmente em edição
        
        # Sistema de log
        self.log_buffer = []
        self.log_lock = Lock()
        self.max_log_lines = 1000  # Limite máximo de linhas no log da UI
        
        # Inicializar componentes
        self.init_ui()
        self.setup_timers()
        
        # Conectar sinal de log
        self.log_signal.connect(self.update_log_display)
        
        # A bandeja deve ser inicializada DEPOIS da UI estar pronta
        QTimer.singleShot(100, self.init_tray)
        
        # Log inicial
        self.log("🚀 Sistema inicializado", "INFO")

    def init_ui(self):
        self.setWindowTitle("Limpeza Automática - Múltiplas Regras")
        self.setFixedSize(700, 800)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)

        # Painel principal
        main_group = QGroupBox("Status do Sistema")
        main_layout = QVBoxLayout()
        
        info_layout = QHBoxLayout()
        
        left_info = QVBoxLayout()
        self.date_label = QLabel("Data: --/--/----")
        self.weekday_label = QLabel("Dia da Semana: ---")
        left_info.addWidget(self.date_label)
        left_info.addWidget(self.weekday_label)
        
        right_info = QVBoxLayout()
        self.time_label = QLabel("Hora: --:--:--")
        self.status_label = QLabel("Status: Pausado")
        self.status_label.setStyleSheet("QLabel { color: #ff4444; font-weight: bold; }")
        right_info.addWidget(self.time_label)
        right_info.addWidget(self.status_label)
        
        info_layout.addLayout(left_info)
        info_layout.addLayout(right_info)
        main_layout.addLayout(info_layout)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)

        # Área de criação/edição de regras
        create_group = QGroupBox("Criar/Editar Regra")
        create_layout = QVBoxLayout()

        # Seleção de pasta
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Pasta:"))
        self.folder_path = QLabel("Nenhuma pasta selecionada")
        self.folder_path.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")
        self.folder_path.setMinimumHeight(30)
        folder_layout.addWidget(self.folder_path, 1)
        
        select_folder_btn = QPushButton("Selecionar...")
        select_folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(select_folder_btn)
        create_layout.addLayout(folder_layout)

        # Horário e dias
        time_days_layout = QHBoxLayout()

        # Horário
        time_layout = QVBoxLayout()
        time_layout.addWidget(QLabel("Horário:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(datetime.now().time())
        time_layout.addWidget(self.time_edit)
        time_days_layout.addLayout(time_layout)

        # Dias da semana
        days_layout = QVBoxLayout()
        days_layout.addWidget(QLabel("Dias da Semana:"))
        days_check_layout = QHBoxLayout()
        
        self.days_checkboxes = {}
        days_eng = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        for eng, pt in zip(days_eng, days_pt):
            cb = QCheckBox(pt)
            self.days_checkboxes[eng] = cb
            days_check_layout.addWidget(cb)
        
        days_layout.addLayout(days_check_layout)
        time_days_layout.addLayout(days_layout)
        create_layout.addLayout(time_days_layout)

        # Botões de ação
        action_buttons_layout = QHBoxLayout()
        
        self.add_rule_btn = QPushButton("Adicionar Regra")
        self.add_rule_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }")
        self.add_rule_btn.clicked.connect(self.add_rule)
        
        self.edit_rule_btn = QPushButton("Salvar Edição")
        self.edit_rule_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; padding: 8px; font-weight: bold; }")
        self.edit_rule_btn.clicked.connect(self.save_edited_rule)
        self.edit_rule_btn.setVisible(False)  # Inicialmente oculto
        
        self.cancel_edit_btn = QPushButton("Cancelar")
        self.cancel_edit_btn.setStyleSheet("QPushButton { background-color: #666; color: white; padding: 8px; font-weight: bold; }")
        self.cancel_edit_btn.clicked.connect(self.cancel_editing)
        self.cancel_edit_btn.setVisible(False)  # Inicialmente oculto
        
        action_buttons_layout.addWidget(self.add_rule_btn)
        action_buttons_layout.addWidget(self.edit_rule_btn)
        action_buttons_layout.addWidget(self.cancel_edit_btn)
        action_buttons_layout.addStretch()
        
        create_layout.addLayout(action_buttons_layout)

        create_group.setLayout(create_layout)
        layout.addWidget(create_group)

        # Lista de regras
        rules_group = QGroupBox("Regras Configuradas")
        rules_layout = QVBoxLayout()
        
        self.rules_list = QListWidget()
        self.rules_list.setAlternatingRowColors(True)
        rules_layout.addWidget(self.rules_list)
        
        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        # Controles gerais
        controls_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Ativar Sistema")
        self.toggle_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; font-weight: bold; }")
        self.toggle_btn.clicked.connect(self.toggle_active)
        
        save_btn = QPushButton("Salvar Tudo")
        save_btn.clicked.connect(self.save_config)
        
        controls_layout.addWidget(self.toggle_btn)
        controls_layout.addWidget(save_btn)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Área de log
        log_group = QGroupBox("Log de Atividades")
        log_layout = QVBoxLayout()
        self.log_area = QLabel("Sistema inicializado. Configure as regras e ative o sistema.")
        self.log_area.setWordWrap(True)
        self.log_area.setAlignment(Qt.AlignTop)
        self.log_area.setStyleSheet("QLabel { background-color: #f8f8f8; padding: 8px; border: 1px solid #ddd; min-height: 60px; }")
        
        log_scroll = QScrollArea()
        log_scroll.setWidget(self.log_area)
        log_scroll.setWidgetResizable(True)
        log_scroll.setFixedHeight(150)
        log_layout.addWidget(log_scroll)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.load_rules_from_config()

    def create_tray_icon(self):
        """Cria um ícone personalizado para a bandeja do sistema"""
        # Criar um ícone simples programaticamente
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Desenhar uma lixeira simples
        painter.setBrush(Qt.red)
        painter.setPen(Qt.darkRed)
        # Corpo da lixeira
        painter.drawRect(8, 6, 16, 14)
        # Tampa da lixeira
        painter.drawRect(6, 4, 20, 4)
        # Detalhes
        painter.setPen(Qt.white)
        painter.drawLine(12, 10, 12, 16)
        painter.drawLine(16, 10, 16, 16)
        painter.drawLine(20, 10, 20, 16)
        
        painter.end()
        
        return QIcon(pixmap)

    def init_tray(self):
        """Inicializa o ícone da bandeja do sistema"""
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.log("⚠ Bandeja do sistema não disponível", "WARNING")
                return

            self.tray_icon = QSystemTrayIcon(self)
            
            # Usar ícone personalizado
            self.tray_icon.setIcon(self.create_tray_icon())
            
            # Criar menu de contexto
            tray_menu = QMenu()
            
            restore_action = tray_menu.addAction("Restaurar")
            restore_action.triggered.connect(self.show_restore)
            
            self.tray_toggle_action = tray_menu.addAction("Ativar Sistema")
            self.tray_toggle_action.triggered.connect(self.toggle_active)
            
            tray_menu.addSeparator()
            
            quit_action = tray_menu.addAction("Sair")
            quit_action.triggered.connect(self.quit_app)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Mostrar ícone
            self.tray_icon.show()
            self.tray_icon.setToolTip("Limpeza Automática de Arquivos")
            
            # Atualizar texto do menu da bandeja
            self.update_tray_menu()
            
            self.log("✅ Ícone da bandeja inicializado com sucesso", "INFO")
            
        except Exception as e:
            self.log(f"❌ Erro ao inicializar bandeja: {str(e)}", "ERROR")

    def update_tray_menu(self):
        """Atualiza o texto do menu da bandeja conforme o estado"""
        if hasattr(self, 'tray_toggle_action'):
            if self.active_mode:
                self.tray_toggle_action.setText("Pausar Sistema")
            else:
                self.tray_toggle_action.setText("Ativar Sistema")

    def show_restore(self):
        """Restaura a janela principal"""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.activateWindow()
        self.raise_()

    def tray_icon_activated(self, reason):
        """Lida com cliques no ícone da bandeja"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_restore()

    def setup_timers(self):
        # Timer para atualizar o relógio
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        # Timer para verificar regras
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_rules)
        self.check_timer.start(30000)  # Verifica a cada 30 segundos

    def update_clock(self):
        now = datetime.now()
        self.date_label.setText(f"Data: {now.strftime('%d/%m/%Y')}")
        
        days_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira",
            "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira",
            "Friday": "Sexta-feira", "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        weekday_pt = days_pt.get(now.strftime("%A"), now.strftime("%A"))
        self.weekday_label.setText(f"Dia da Semana: {weekday_pt}")
        
        self.time_label.setText(f"Hora: {now.strftime('%H:%M:%S')}")

    def check_rules(self):
        if not self.active_mode:
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%a")
        today_date = now.strftime("%Y-%m-%d")

        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            widget = self.rules_list.itemWidget(item)
            if widget:
                rule = widget.rule_data
                
                if (current_day in rule["days"] and 
                    current_time == rule["time"] and
                    self.active_mode):
                    
                    rule_key = f"{rule['folder']}_{rule['time']}_{current_day}"
                    if self.execution_history.get(rule_key) != today_date:
                        self.execution_history[rule_key] = today_date
                        Thread(target=self.execute_rule, args=(rule,), daemon=True).start()

    def force_delete_file(self, file_path):
        """Força a exclusão de um arquivo individual"""
        try:
            # Remove atributos de somente leitura, ocultos, etc.
            if os.path.isfile(file_path):
                os.chmod(file_path, 0o777)  # Dar permissões totais
                os.unlink(file_path)  # Excluir arquivo
                return True
        except Exception as e:
            # Método alternativo: mover para temp e excluir
            try:
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, f"temp_delete_{os.path.basename(file_path)}")
                if os.path.exists(file_path):
                    shutil.move(file_path, temp_path)
                    if os.path.exists(temp_path):
                        os.chmod(temp_path, 0o777)
                        os.unlink(temp_path)
                return True
            except Exception:
                pass
        return False

    def delete_directory_contents(self, directory_path, rule):
        """Exclui recursivamente todo o conteúdo de um diretório (arquivos e subpastas)"""
        deleted_count = 0
        error_count = 0
        
        try:
            # Primeiro, processar todos os itens no diretório
            for item_name in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item_name)
                
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        # É arquivo ou link simbólico
                        if self.force_delete_file(item_path):
                            # Log detalhado do arquivo excluído
                            self.log(f"📄 ARQUIVO EXCLUÍDO: {item_path} (Regra: {os.path.basename(rule['folder'])} - {rule['time']})", "DELETE")
                            deleted_count += 1
                        else:
                            error_count += 1
                            self.log(f"❌ Falha ao excluir arquivo: {item_path}", "ERROR")
                            
                    elif os.path.isdir(item_path):
                        # É subpasta - excluir recursivamente
                        sub_deleted, sub_errors = self.delete_directory_contents(item_path, rule)
                        deleted_count += sub_deleted
                        error_count += sub_errors
                        
                        # Agora excluir a própria subpasta (vazia)
                        try:
                            os.chmod(item_path, 0o777)
                            os.rmdir(item_path)
                            # Log detalhado da pasta excluída
                            self.log(f"📁 PASTA EXCLUÍDA: {item_path} (Regra: {os.path.basename(rule['folder'])} - {rule['time']})", "DELETE")
                            deleted_count += 1
                        except Exception as e:
                            error_count += 1
                            self.log(f"❌ Falha ao excluir pasta {item_path}: {str(e)}", "ERROR")
                            
                except Exception as e:
                    error_count += 1
                    self.log(f"⚠ Erro ao processar {item_name}: {str(e)}", "WARNING")
                    
        except Exception as e:
            self.log(f"❌ Erro ao listar diretório {directory_path}: {str(e)}", "ERROR")
            error_count += 1
            
        return deleted_count, error_count

    def execute_rule(self, rule):
        """Executa uma regra de limpeza em thread separada"""
        try:
            folder_path = rule['folder']
            rule_name = f"{os.path.basename(folder_path)} - {rule['time']}"
            
            self.log(f"🚀 INICIANDO REGRA: {rule_name}", "INFO")
            
            if not os.path.exists(folder_path):
                self.log(f"❌ Erro: Pasta não encontrada - {folder_path}", "ERROR")
                return

            if not os.access(folder_path, os.W_OK):
                self.log(f"❌ Erro: Sem permissão de escrita - {folder_path}", "ERROR")
                return

            start_time = time.time()
            
            # Excluir todo o conteúdo da pasta (arquivos E subpastas)
            deleted_count, error_count = self.delete_directory_contents(folder_path, rule)
            
            execution_time = time.time() - start_time
            
            if error_count == 0:
                self.log(f"✅ REGRA CONCLUÍDA: {rule_name} - {deleted_count} itens excluídos em {execution_time:.1f}s", "SUCCESS")
            else:
                self.log(f"⚠ REGRA PARCIAL: {rule_name} - {deleted_count} itens excluídos, {error_count} erros em {execution_time:.1f}s", "WARNING")
                
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO na regra {rule['folder']}: {str(e)}", "ERROR")

    def log(self, message, level="INFO"):
        """Sistema de log robusto e thread-safe"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Mapear níveis para emojis/cores
            level_icons = {
                "INFO": "ℹ️",
                "SUCCESS": "✅", 
                "WARNING": "⚠️",
                "ERROR": "❌",
                "DELETE": "🗑️"
            }
            
            icon = level_icons.get(level, "🔵")
            log_entry = f"[{timestamp}] {icon} {message}"
            
            # Adicionar ao buffer (com lock para thread-safety)
            with self.log_lock:
                self.log_buffer.append(log_entry)
                
                # Manter apenas as linhas mais recentes no buffer
                if len(self.log_buffer) > self.max_log_lines:
                    self.log_buffer = self.log_buffer[-self.max_log_lines:]
            
            # Escrever no arquivo de log
            self.write_to_log_file(log_entry)
            
            # Emitir sinal para atualizar a UI (thread-safe)
            self.log_signal.emit(log_entry)
            
        except Exception as e:
            print(f"Erro no sistema de log: {str(e)}")

    def write_to_log_file(self, log_entry):
        """Escreve uma entrada no arquivo de log"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Erro ao escrever no arquivo de log: {str(e)}")

    def update_log_display(self, log_entry):
        """Atualiza a exibição do log na UI (chamada via signal)"""
        try:
            current_text = self.log_area.text()
            
            # Limitar o número de linhas exibidas para evitar lentidão
            lines = current_text.split('\n')
            if len(lines) > 200:  # Manter apenas as 200 linhas mais recentes na UI
                lines = lines[:200]
                current_text = '\n'.join(lines)
            
            # Adicionar nova linha no topo
            new_text = log_entry + "\n" + current_text
            self.log_area.setText(new_text)
            
        except Exception as e:
            print(f"Erro ao atualizar display do log: {str(e)}")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Limpeza")
        if folder:
            self.folder_path.setText(folder)

    def add_rule(self):
        folder = self.folder_path.text()
        if folder == "Nenhuma pasta selecionada" or not folder.strip():
            QMessageBox.warning(self, "Aviso", "Selecione uma pasta primeiro!")
            return

        selected_days = [day for day, cb in self.days_checkboxes.items() if cb.isChecked()]
        if not selected_days:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um dia da semana!")
            return

        rule_time = self.time_edit.time().toString("HH:mm")
        
        rule_data = {
            "folder": folder,
            "time": rule_time,
            "days": selected_days
        }

        # Verificar se regra já existe
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            widget = self.rules_list.itemWidget(item)
            if (widget and widget.rule_data["folder"] == folder and 
                widget.rule_data["time"] == rule_time):
                QMessageBox.warning(self, "Aviso", "Esta regra já existe!")
                return

        self.add_rule_to_list(rule_data)
        self.log(f"📝 Regra adicionada: {os.path.basename(folder)} às {rule_time}", "INFO")
        
        # Limpar campos após adicionar
        self.clear_rule_fields()

    def add_rule_to_list(self, rule_data):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 60))  # Altura fixa para o item
        
        widget = RuleWidget(rule_data, self.remove_rule, self.edit_rule)
        self.rules_list.addItem(item)
        self.rules_list.setItemWidget(item, widget)

    def remove_rule(self, rule_data):
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            widget = self.rules_list.itemWidget(item)
            if (widget and widget.rule_data["folder"] == rule_data["folder"] and
                widget.rule_data["time"] == rule_data["time"]):
                self.rules_list.takeItem(i)
                self.log(f"🗑️ Regra removida: {os.path.basename(rule_data['folder'])}", "INFO")
                break

    def edit_rule(self, rule_data):
        """Inicia a edição de uma regra existente"""
        self.editing_rule = rule_data
        
        # Preencher os campos com os dados da regra
        self.folder_path.setText(rule_data['folder'])
        self.time_edit.setTime(datetime.strptime(rule_data['time'], '%H:%M').time())
        
        # Marcar os dias da semana
        for day, cb in self.days_checkboxes.items():
            cb.setChecked(day in rule_data['days'])
        
        # Alterar a interface para modo de edição
        self.add_rule_btn.setVisible(False)
        self.edit_rule_btn.setVisible(True)
        self.cancel_edit_btn.setVisible(True)
        
        self.log(f"✏️ Editando regra: {os.path.basename(rule_data['folder'])}", "INFO")

    def save_edited_rule(self):
        """Salva las alterações de uma regra em edição"""
        if not self.editing_rule:
            return
            
        folder = self.folder_path.text()
        if folder == "Nenhuma pasta selecionada" or not folder.strip():
            QMessageBox.warning(self, "Aviso", "Selecione uma pasta primeiro!")
            return

        selected_days = [day for day, cb in self.days_checkboxes.items() if cb.isChecked()]
        if not selected_days:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um dia da semana!")
            return

        rule_time = self.time_edit.time().toString("HH:mm")
        
        new_rule_data = {
            "folder": folder,
            "time": rule_time,
            "days": selected_days
        }

        # Verificar se a nova regra conflita com outra existente (excluindo a que está sendo editada)
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            widget = self.rules_list.itemWidget(item)
            if (widget and widget.rule_data == self.editing_rule):
                continue  # Pular a regra que está sendo editada
                
            if (widget and widget.rule_data["folder"] == folder and 
                widget.rule_data["time"] == rule_time):
                QMessageBox.warning(self, "Aviso", "Já existe uma regra com esta pasta e horário!")
                return

        # Atualizar a regra na lista
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            widget = self.rules_list.itemWidget(item)
            if (widget and widget.rule_data == self.editing_rule):
                widget.rule_data = new_rule_data
                widget.update_display()
                break

        self.log(f"✅ Regra editada: {os.path.basename(folder)} às {rule_time}", "SUCCESS")
        
        # Sair do modo de edição
        self.cancel_editing()

    def cancel_editing(self):
        """Cancela a edição atual e retorna ao modo normal"""
        self.editing_rule = None
        self.clear_rule_fields()
        
        # Restaurar interface para modo normal
        self.add_rule_btn.setVisible(True)
        self.edit_rule_btn.setVisible(False)
        self.cancel_edit_btn.setVisible(False)

    def clear_rule_fields(self):
        """Limpa os campos de entrada de regra"""
        self.folder_path.setText("Nenhuma pasta selecionada")
        self.time_edit.setTime(datetime.now().time())
        for cb in self.days_checkboxes.values():
            cb.setChecked(False)

    def toggle_active(self):
        self.active_mode = not self.active_mode
        self.update_status()
        self.update_tray_menu()  # Atualizar menu da bandeja
        self.save_config()

    def update_status(self):
        if self.active_mode:
            self.status_label.setText("Status: ATIVO")
            self.status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
            self.toggle_btn.setText("Pausar Sistema")
            self.toggle_btn.setStyleSheet("QPushButton { background-color: #ff9800; color: white; padding: 8px; font-weight: bold; }")
            self.log("🟢 Sistema ATIVADO - Regras em execução automática", "SUCCESS")
        else:
            self.status_label.setText("Status: Pausado")
            self.status_label.setStyleSheet("QLabel { color: #ff4444; font-weight: bold; }")
            self.toggle_btn.setText("Ativar Sistema")
            self.toggle_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; font-weight: bold; }")
            self.log("🔴 Sistema PAUSADO", "INFO")

    def load_config(self):
        default = {
            "active": False,
            "rules": []
        }
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Erro ao carregar configurações: {str(e)}", "ERROR")
        return default

    def save_config(self):
        try:
            rules = []
            for i in range(self.rules_list.count()):
                item = self.rules_list.item(i)
                widget = self.rules_list.itemWidget(item)
                if widget:
                    rules.append(widget.rule_data)

            config = {
                "active": self.active_mode,
                "rules": rules
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            self.log("💾 Configurações salvas com sucesso!", "SUCCESS")
            
        except Exception as e:
            self.log(f"❌ Erro ao salvar configurações: {str(e)}", "ERROR")

    def load_rules_from_config(self):
        for rule_data in self.config.get("rules", []):
            self.add_rule_to_list(rule_data)
        
        self.active_mode = self.config.get("active", False)
        self.update_status()
        
        if self.config.get("rules"):
            self.log(f"📂 Carregadas {len(self.config['rules'])} regras da configuração anterior", "INFO")

    def closeEvent(self, event):
        """Lida com o fechamento da janela - minimiza para bandeja"""
        event.ignore()
        self.hide()
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Limpeza Automática",
                "O aplicativo continua executando em segundo plano",
                QSystemTrayIcon.Information,
                2000
            )

    def quit_app(self):
        """Encerra o aplicativo completamente"""
        self.log("👋 Encerrando aplicativo...", "INFO")
        self.save_config()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()


if __name__ == "__main__":
    # Configurar aplicação ANTES de criar a janela
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # IMPORTANTE: Não fechar app quando janela fechar
    app.setApplicationName("Limpeza Automática")
    app.setApplicationVersion("3.0")
    
    # Verificar se a bandeja do sistema está disponível
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Sistema", 
                           "A bandeja do sistema não está disponível neste sistema.\n"
                           "O aplicativo não pode funcionar corretamente.")
        sys.exit(1)
    
    # Criar e mostrar janela
    window = FileCleanerApp()
    window.show()
    
    sys.exit(app.exec_())