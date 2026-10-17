"""Tabby: wires the API together. Each part edits only its own file."""

from fastapi import FastAPI

from app import bills

app = FastAPI(title="Tabby")
app.include_router(bills.router)
