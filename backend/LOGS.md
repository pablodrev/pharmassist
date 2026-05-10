# Logs

## 2026-05-08

### Added comprehensive test suite (84 tests)

Created tests covering all main use cases from the technical specification.

**New files:**
- `tests/test_auth_extended.py` — registration validation (role, password length, email format), login edge cases, profile, password change
- `tests/test_reports_details.py` — report GET (own/other/specialist/404), analysis status, list/filter/pagination, status transitions, specialist review overrides, finalization, reanalysis, form submission, file extraction
- `tests/test_drugs.py` — drug search by Russian/English name, auth guard, query validation, result limit
- `tests/test_rag.py` — RAG document list/upload/delete with role-based access control
- `tests/test_analysis_pipeline.py` — full pipeline with mocked orchestrator: all 5 recommendation types (case extraction, IME, Naranjo, expectedness, completeness), analysis failure path, DOCX extraction

**Modified:**
- `tests/conftest.py` — added JSONB→TEXT DDL patch for SQLite compatibility (fixed pre-existing breakage in original tests), added `drugs_in_db` fixture
