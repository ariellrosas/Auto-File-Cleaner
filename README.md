# 🧹 Auto File Cleaner

Desktop application that automatically cleans folders based on scheduled rules.

Aplicativo desktop que limpa automaticamente pastas de acordo com regras programadas.

---

# 🇺🇸 English

## 📌 Overview

**Auto File Cleaner** is a desktop application developed in Python that allows users to automatically clean folders based on scheduled rules.

Instead of manually deleting temporary files or unused content, the application executes cleaning tasks automatically according to configured schedules.

This project was developed as a **portfolio project** and also solves a real-world problem of repetitive manual file deletion.

---

## ✨ Features

* 🕒 Scheduled folder cleaning
* 📅 Day-of-week scheduling
* 📂 Multiple folder rules
* 🖥 Graphical user interface
* 🔄 Background execution
* 📌 System tray integration
* 🧾 Activity logging
* ⚙ Configurable rules

---

## 🧠 Use Cases

Auto File Cleaner is useful for scenarios such as:

* Cleaning **temporary folders**
* Cleaning **download folders**
* Managing **incoming files folders**
* Removing files from folders that accumulate unnecessary content
* Automating repetitive file maintenance tasks

---

## 🛠 Technologies Used

* **Python**
* **PyQt5** (GUI framework)

---

## ⚙ Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/auto-file-cleaner.git
```

Enter the project folder:

```bash
cd auto-file-cleaner
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶ Running the Application

Run the program with:

```bash
python src/auto_file_cleaner.py
```

---

## 📦 Building the Executable (.exe)

You can convert the project into a Windows executable using **PyInstaller**.

Install PyInstaller:

```bash
pip install pyinstaller
```

Build the executable:

```bash
pyinstaller --onefile --windowed src/auto_file_cleaner.py
```

The executable will be generated in the `dist` folder.

---

## ⚙ Configuration

The application uses a configuration file (`config.json`) where cleaning rules are stored.

Example:

```json
{
  "active": true,
  "rules": [
    {
      "folder": "D:/Downloads",
      "time": "15:30",
      "days": ["Tue"]
    }
  ]
}
```

Each rule defines:

* Folder to clean
* Execution time
* Days of the week

---

## 🧾 Logs

The application generates logs that record cleaning operations and system events.

Example:

```
[2025-11-18 15:30:29] FILE DELETED
[2025-11-18 15:30:29] RULE COMPLETED
```

---

## ⚠ Disclaimer

This software permanently deletes files from configured folders.
Make sure the selected folders **do not contain important data**.

Use it carefully.

---

## 👨‍💻 Author

Developed by **Ariel** as a portfolio project.

---

# 🇧🇷 Português

## 📌 Visão Geral

**Auto File Cleaner** é um aplicativo desktop desenvolvido em Python que permite limpar automaticamente pastas com base em regras programadas.

Em vez de deletar arquivos manualmente, o aplicativo executa tarefas de limpeza automaticamente de acordo com os horários definidos.

Este projeto foi desenvolvido como **projeto de portfólio** e também para resolver um problema real de exclusão repetitiva de arquivos.

---

## ✨ Funcionalidades

* 🕒 Limpeza automática por horário
* 📅 Agendamento por dias da semana
* 📂 Suporte a múltiplas regras
* 🖥 Interface gráfica
* 🔄 Execução em segundo plano
* 📌 Integração com bandeja do sistema
* 🧾 Registro de logs
* ⚙ Regras configuráveis

---

## 🧠 Casos de Uso

O Auto File Cleaner pode ser usado para:

* Limpar **pastas temporárias**
* Limpar **pastas de download**
* Organizar **pastas de arquivos recebidos**
* Remover arquivos acumulados automaticamente
* Automatizar tarefas repetitivas de manutenção

---

## 🛠 Tecnologias Utilizadas

* **Python**
* **PyQt5** (interface gráfica)

---

## ⚙ Instalação

Clone o repositório:

```bash
git clone https://github.com/seuusuario/auto-file-cleaner.git
```

Entre na pasta do projeto:

```bash
cd auto-file-cleaner
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## ▶ Executando o Programa

Execute o aplicativo com:

```bash
python src/auto_file_cleaner.py
```

---

## 📦 Gerando o Executável (.exe)

Você pode converter o projeto em um executável do Windows usando **PyInstaller**.

Instale o PyInstaller:

```bash
pip install pyinstaller
```

Gere o executável:

```bash
pyinstaller --onefile --windowed src/auto_file_cleaner.py
```

O executável será gerado na pasta `dist`.

---

## ⚙ Configuração

O aplicativo utiliza um arquivo `config.json` para armazenar as regras.

Exemplo:

```json
{
  "active": true,
  "rules": [
    {
      "folder": "D:/Downloads",
      "time": "15:30",
      "days": ["Tue"]
    }
  ]
}
```

Cada regra define:

* Pasta a ser limpa
* Horário de execução
* Dias da semana

---

## 🧾 Logs

O aplicativo gera registros de log com as atividades do sistema e exclusões realizadas.

Exemplo:

```
[2025-11-18 15:30:29] ARQUIVO EXCLUÍDO
[2025-11-18 15:30:29] REGRA CONCLUÍDA
```

---

## ⚠ Aviso

Este software remove arquivos permanentemente das pastas configuradas.

Certifique-se de que as pastas selecionadas **não contenham arquivos importantes**.
