# AGENTS.md

## Krótki opis
Ten plik dokumentuje agentów (automatyzowane procesy, worker-y, skrypty zaplanowane lub LLM‑driven tools) używanych w projekcie "Polish-Football-Data-Hub-International". Celem jest:
- wyjaśnić cel każdego agenta,
- określić uprawnienia i wymagane sekrety,
- opisać bezpieczne działanie, testowanie i monitorowanie,
- podać przykłady użycia i szablony promptów.

Utrzymuj ten dokument aktualnym przy każdej zmianie w agentach.

---

## Szybkie streszczenie agentów (zalecany podział)
Podział agentów jest sugestią; dostosuj do rzeczywistej struktury projektu:

- Data Ingestor
  - Cel: pobieranie transferów, statystyk i zmian w statusie zawodników z zewnętrznych źródeł (API lig, strony klubów, open data).
  - Format wyjściowy: surowe JSON do katalogu `data/raw/` oraz zapis do tabeli staging w Supabase.
- Player Updater
  - Cel: przetwarzanie danych z staging i synchronizacja do głównych tabel (players, clubs, appearances).
  - Wyzwalanie: cron lub webhook; idempotentny.
- Stats Aggregator
  - Cel: agregacja meczowych/w sezonowych statystyk oraz obliczanie metryk.
  - Rezultat: tabele/kolumny gotowe do zapytań w UI.
- Notification Agent
  - Cel: wysyłka powiadomień (np. Slack/email) o ważnych zmianach: transfery, kontuzje, nowe zawodniki w bazie.
  - Ograniczenia: throttle, retry, i human approval dla ważnych komunikatów.
- Maintenance / Housekeeping
  - Cel: kasowanie starych logów, optymalizacja DB, archiwizacja.

---

## Uprawnienia i sekrety
Zasada: najmniejsze uprawnienia (principle of least privilege).

Wymagane poświadczenia:
- SUPABASE_URL i SUPABASE_SERVICE_ROLE_KEY (lub lepiej: klucz serwisowy o ograniczonych prawach)
  - Jeśli agent tylko czyta/zapisuje specyficzne tabele, utwórz role z ograniczonymi uprawnieniami.
- EXTERNAL_API_KEYS (np. API lig, scraping proxies)
- SLACK_WEBHOOK / EMAIL_SMTP credentials

Dobre praktyki:
- Nie przechowuj sekretów w kodzie. Użyj GitHub Secrets / environment variables / secret manager (AWS/GCP/HashiCorp Vault).
- Ogranicz widoczność sekretów w CI: tylko workflow-y potrzebujące agentów powinny mieć dostęp.
- Rekonfiguruj/rotuj klucze okresowo.

---

## Zakres działań — co agent może, a czego nie może robić
Dozwolone:
- czytanie/aktualizacja tabel związanych z zawodnikami, klubami, statystykami;
- wysyłka powiadomień przy spełnionych warunkach;
- zaplanowane pobrania i retry on failure.

Zabronione:
- modyfikowanie konfiguracji serwera lub infra (przez agentów bez jawnej autoryzacji);
- eksport danych osobowych poza zatwierdzone kanały;
- używanie SUPABASE_SERVICE_ROLE_KEY do bezpośredniego generowania publicznych kluczy.

---

## Bezpieczeństwo i prywatność
- Minimalizuj dane osobowe w logach (PII masking).
- Przed wysyłką zewnętrzną (np. Slack) weryfikuj, czy dane mogą być ujawnione.
- Wdroż retry/backoff i circuit breaker dla zewnętrznych API.
- Waliduj i sanityzuj dane z zewnętrznych źródeł przed zapisem do DB.

---

## Monitorowanie i obserwowalność
Rekomendowane komponenty:
- Logging: strukturalne logi (JSON) z poziomami (INFO/WARN/ERROR) i request_id/trace_id.
- Metrics: liczniki sukcesów/porażek, latency, queue depth (Prometheus).
- Tracing: OpenTelemetry dla krytycznych ścieżek.
- Alerting: Sentry/PagerDuty/Slack dla krytycznych błędów (np. nieudana synchronizacja > N razy).
- Audyt: zapis akcji krytycznych (kto/który agent, co zmienił, kiedy).

Przykładowe metryki:
- ingestion.success_count
- ingestion.failure_count
- updater.rows_processed
- notifications.sent_count
- db.write_errors

---

## Testowanie i walidacja
- Unit tests: logika parsowania, mapowania pól, sanity checks.
- Integration tests: testy end-to-end z tymczasową instancją Supabase (może być lokalna baza w CI).
- Contract tests: testy schematu danych przychodzących (JSON Schema).
- Regression tests: przykładowe pliki danych w fixtures.
- CI: uruchamiaj testy przy każdym PR; dodaj krok lintowania i bezpieczeństwa (bandit for Python).

---

## Uruchamianie lokalne i w produkcji
Przykłady (dostosuj do rzeczywistej struktury kodu):
- Uruchomienie pojedynczego agenta lokalnie:
  - export SUPABASE_URL=...
  - export SUPABASE_KEY=...
  - python -m agents.data_ingest --config config/local.yaml
- Docker (zalecane):
  - Stwórz Dockerfile dla agentów i docker-compose z service dla agenta + lokalny Supabase/Postgres.
- Scheduler:
  - Cron, systemd timers, Kubernetes CronJob, lub Airflow (jeśli projekt rośnie).

---

## Fail-safe i rollback
- Operacje mutacyjne powinny być idempotentne i atomowe (transaction rollback).
- Zawsze twórz backup tabel krytycznych przed krótkimi migracjami.
- W krytycznych zmianach: require human approval przed propagacją (manual gate).
- Możliwość wyłączenia agenta (maintenance mode) przez flagę w DB/Config.

---

## Observability of Changes (Audyt)
- Każdy zapis do głównych tabel powinien mieć metadata: source_agent, source_version, changed_by, occurred_at.
- Pozwala to śledzić, który agent wygenerował zmianę i co przyczyniło się do ewentualnych regresji.

---

## Przykładowe workflowy i szablony promptów / inputów
1) Ingest new match data (cron)
- Input: endpoint URL, date range
- Output: zapis do data/raw/ oraz staging table

2) Manual trigger: "Aktualizuj zawodnika X"
- Szablon: `python -m agents.player_update --player-id 12345 --force`
- Warunki: tylko uruchomione przez roota/CI lub użytkownika z uprawnieniem "operator".

3) Notification (LLM-driven summary)
- Prompt template (jeśli generujesz opis zmian przez LLM):
  - "Stwórz krótki tweet o transferze: {player_name} przeszedł do {club_name}. Powiadomienia: {key_stats}. Nie używaj danych wrażliwych."

---

## Ograniczenia i znane ryzyka
- Dane zewnętrzne mogą być niekompletne/nieprawidłowe — wymagaj sanity checks.
- LLM-driven agents: generowanie treści musi przejść filtr bezpieczeństwa (no PII leak).
- Zależność od zewnętrznych API (rate limits) — przygotuj cache i retry.

---

## Kto za to odpowiada (proponowane role)
- Właściciel: @LenartDominik — ogólna odpowiedzialność za projekt.
- Maintainer agentów: osoba odpowiedzialna za implementację i CI (zaznacz w README/CONTRIBUTING).
- On-call: osoba do pageringu w razie poważnych incydentów.

---

## Dodawanie/zmiana agenta — checklista PR
- [ ] Opis celu w AGENTS.md z aktualizacją.
- [ ] Unit + integration tests.
- [ ] Lint i static analysis.
- [ ] Dokumentacja sekretów i wymagań infra.
- [ ] Dodanie metryk i logowania.
- [ ] Review (co najmniej 1 reviewer).

---

## Aktualizacje i wersjonowanie
- Numeruj wersje agentów (np. agent_name@v1.2.0).
- Aktualizuj AGENTS.md przy zmianie zachowania lub uprawnień.

---

## FAQ krótkie
Q: Czy agent może od razu pushować poprawki do produkcji?  
A: Tylko jeśli ma wyraźne uprawnienia i proces akceptacji. Zalecane: deployowane PR → manual approval.

Q: Gdzie trzymać sekrety?  
A: GitHub Secrets / Secret Manager. Nigdy w repo.
