# Decisions log

- Initial implementation uses `Base.metadata.create_all()` at app startup for a zero-friction first run; Alembic environment is included for versioned schema changes, and production deployments should use migrations.
- The initial UI is consolidated into role-filtered Streamlit navigation to keep the first runnable release compact; service logic remains outside page code.
- Arabic font styling falls back to locally installed system fonts rather than downloading a web font, preserving offline operation.
- Work-order numbering uses yearly count-plus-one for the single-server MVP; deployments with concurrent high-volume creation should move sequence allocation into a transactional counter.

- `streamlit_app.py` is the sole documented entrypoint and adds the repository root to `sys.path` to avoid accidental Alembic entrypoint selection.
- Cloud demo mode uses the OS temporary directory for SQLite and shows an Arabic demo-data warning; the filesystem is ephemeral and not suitable for durable records.
- Shift/window defaults use the Damascus timezone, while persisted event timestamps continue to use UTC-naive values to match the existing schema.
- The engineer work-order inbox can resume a waiting-parts order into repair and notify nurses in the affected department.
- Cloud deployment instructions explicitly enable `DEMO_MODE` and caution that the MVP is not clinically validated.
