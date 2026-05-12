# 1. Używamy lekkiej wersji Pythona
FROM python:3.12-slim

# 2. Ustawiamy folder roboczy wewnątrz kontenera
WORKDIR /app

# 3. Kopiujemy listę bibliotek i instalujemy je
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kopiujemy całą resztę kodu projektu do kontenera
COPY . .

# 5. Informujemy, że aplikacja działa na porcie 8000
EXPOSE 8000

# 6. Komenda, która uruchamia nasz bank
CMD ["uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000"]