# PDF Parser Baseline (Docling + Gemma 3 VLM)

Модульный конвейер для высокоточного извлечения текста и таблиц из PDF.

## Архитектура
* **Core:** Нативный парсинг с помощью `docling` (TableFormerMode.ACCURATE).
* **AI:** Использование `some` для извлечения данных из сложных схем и изображений.
* **Постобработка:** Конвертация HTML-таблиц в Markdown строго по ТЗ (дублирование ячеек, склейка заголовков) и алгоритм Fuzzy Matching (65%) для устранения дубликатов текста от OCR.

## Запуск
1. Установите зависимости (docling, openai, python-dotenv, pillow).
2. Скопируйте `.env.example` в `.env` и добавьте ваш `API_KEY`.
3. Запустите скрипт:
```bash
python main.py --input-dir ./pdfs --output-dir ./results --full-quality  
  
ВАЖНО! Для запуска использовалась версия python3.12.3!