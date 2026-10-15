"""Тохиргоо: орчны хувьсагч, эсвэл Streamlit secrets (.streamlit/secrets.toml)."""
import os


def setting(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except Exception:
        return default
