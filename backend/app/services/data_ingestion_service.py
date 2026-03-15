"""Data ingestion service – stub."""
import pandas as pd

async def bulk_insert_attendance(db, df: pd.DataFrame, recorded_by: int):
    return {"inserted": len(df), "skipped": 0, "errors": []}
