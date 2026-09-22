import flet as ft
import json
import os
from pathlib import Path
from pypdf import PdfReader
from docx import Document

DB_FILE = "brain_db.json"


class SecondBrain:
    def __init__(self):
        self.db = self._load_db()

    def _load_db(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"documents": []}

    def _save_db(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.db, f, ensure_ascii=False, indent=2)

    def extract_text(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(file_path)
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        elif suffix == ".docx":
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        else:
            raise ValueError(f"Неподдерживаемый формат: {suffix}")

    def add_document(self, file_path):
        text = self.extract_text(file_path)
        if not text.strip():
            raise ValueError("Файл пустой.")
        self.db["documents"].append({
            "name": os.path.basename(file_path),
            "text": text[:5000]
        })
        self._save_db()
        return os.path.basename(file_path)

    def search(self, query, top_k=3):
        docs = self.db["documents"]
        if not docs:
            return []
        query_words = set(query.lower().split())
        scored = []
        for d in docs:
            text_words = set(d["text"].lower().split())
            score = len(query_words & text_words) / max(len(query_words), 1)
            scored.append((d, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"name": d["name"], "text": d["text"], "score": float(s)}
            for d, s in scored[:top_k]
        ]


def main(page: ft.Page):
    page.title = "Второй мозг"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    brain = SecondBrain()
    status = ft.Text("Готов", color=ft.Colors.GREEN)
    picker = ft.FilePicker()
    page.overlay.append(picker)
    search_field = ft.TextField(label="Поиск", expand=True)
    results = ft.Column(spacing=10)

    def on_pick(e):
        if not e.files:
            return
        status.value = "Обработка..."
        page.update()
        try:
            name = brain.add_document(e.files[0].path)
            status.value = f"✅ {name}"
            status.color = ft.Colors.GREEN
        except Exception as ex:
            status.value = f"❌ {ex}"
            status.color = ft.Colors.RED
        page.update()

    def on_search(e):
        results.controls.clear()
        found = brain.search(search_field.value.strip())
        if not found:
            results.controls.append(ft.Text("Ничего не найдено"))
        for r in found:
            results.controls.append(
                ft.Card(content=ft.Container(
                    content=ft.Column([
                        ft.Text(r["name"], weight=ft.FontWeight.BOLD),
                        ft.Text(f"Схожесть: {r['score']:.2f}"),
                        ft.Text(r["text"][:300] + "...", size=12)
                    ]),
                    padding=10
                ))
            )
        page.update()

    page.add(
        ft.Text("🧠 Второй мозг", size=30, weight=ft.FontWeight.BOLD),
        status,
        ft.ElevatedButton("📁 Добавить PDF/DOCX",
                          icon=ft.Icons.UPLOAD_FILE,
                          on_click=lambda _: picker.pick_files(
                              allowed_extensions=["pdf", "docx"])),
        ft.Row([search_field,
                ft.ElevatedButton("🔍 Найти", on_click=on_search)]),
        ft.Divider(),
        results
    )


ft.app(target=main)
