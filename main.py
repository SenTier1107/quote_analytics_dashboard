from fastapi import FastAPI
import gradio as gr

from core.database import init_db
from api.quotes import router as quotes_router
from api.stats import router as stats_router
from api.favorites import router as favorites_router
from ui.app import create_ui
from api.authors import router as authors_router

app = FastAPI(
    title="Quote Insight Dashboard API",
    description="FastAPI 기반 격언 관리 및 분석 시스템",
    version="0.1.0"
)

init_db()

app.include_router(quotes_router)
app.include_router(stats_router)
app.include_router(favorites_router)
app.include_router(authors_router)

@app.get("/")
def root():
    return {
        "message": "Quote Insight Dashboard API",
        "docs": "/docs",
        "gradio": "/dashboard"
    }


demo = create_ui()
demo.theme = gr.themes.Soft()
app = gr.mount_gradio_app(app, demo, path="/dashboard")