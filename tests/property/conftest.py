# -*- coding: utf-8 -*-
"""Стратегии Hypothesis для property-based тестов Interior Studio CRM."""

import os
import sys

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
# Добавляем server/ для импорта серверных модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

from hypothesis import strategies as st
import pytest

# === Стратегии для площадей ===
# Реальные площади квартир/домов: от 10 до 5000 м²
areas = st.floats(min_value=0.1, max_value=50000.0, allow_nan=False, allow_infinity=False)
realistic_areas = st.floats(min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False)

# === Стратегии для тарифов ===
rates = st.floats(min_value=1.0, max_value=500000.0, allow_nan=False, allow_infinity=False)
rate_per_m2 = st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)

# === Стратегии для времени ===
hours = st.integers(min_value=0, max_value=744)  # макс часов в месяце
working_days = st.integers(min_value=1, max_value=365)
contract_terms = st.integers(min_value=1, max_value=500)  # рабочие дни по договору

# === Стратегии для процентов ===
percentages = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)

# === Стратегии для дат ===
date_strings_iso = st.dates(
    min_value=__import__("datetime").date(2020, 1, 1),
    max_value=__import__("datetime").date(2030, 12, 31),
).map(lambda d: d.strftime("%Y-%m-%d"))

date_strings_ru = st.dates(
    min_value=__import__("datetime").date(2020, 1, 1),
    max_value=__import__("datetime").date(2030, 12, 31),
).map(lambda d: d.strftime("%d.%m.%Y"))

# === Стратегии для типов проектов ===
project_type_codes = st.sampled_from([1, 2, 3])  # 1=Полный, 2=Эскизный, 3=Планировочный
project_types = st.sampled_from(["Индивидуальный", "Шаблонный"])
template_subtypes = st.sampled_from(
    [
        "Стандарт",
        "Стандарт с визуализацией",
        "Проект ванной комнаты",
        "Проект ванной комнаты с визуализацией",
    ]
)

# === Стратегии для этажей ===
floors = st.integers(min_value=1, max_value=5)

# === Стратегии для месяцев (ГГГГ-ММ) ===
month_strings = st.tuples(
    st.integers(min_value=2020, max_value=2030),
    st.integers(min_value=1, max_value=12),
).map(lambda ym: f"{ym[0]}-{ym[1]:02d}")
