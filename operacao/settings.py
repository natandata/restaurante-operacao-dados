"""Configuração local. Diretórios de dados são privados e não versionados."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('RESTAURANTE_DATA', str(ROOT / 'data')))
RAW = DATA / 'generated'
SQLITE = DATA / 'operations.sqlite3'
WAREHOUSE = DATA / 'restaurant.duckdb'
CHANNEL_FEES = {'salao': 0.0, 'retirada': 0.03, 'entrega': 0.18}
PRODUCTS = [
    {'id': 'P01', 'name': 'Prato de arroz e feijão', 'category': 'prato', 'price_cents': 2600, 'cost_cents': 880},
    {'id': 'P02', 'name': 'Bowl de legumes', 'category': 'prato', 'price_cents': 2300, 'cost_cents': 760},
    {'id': 'P03', 'name': 'Porção de batata', 'category': 'acompanhamento', 'price_cents': 1200, 'cost_cents': 360},
    {'id': 'P04', 'name': 'Suco da casa', 'category': 'bebida', 'price_cents': 800, 'cost_cents': 210},
]
INGREDIENTS = [
    {'id': 'I01', 'name': 'Arroz', 'unit': 'g', 'opening': 25000, 'reorder': 7000},
    {'id': 'I02', 'name': 'Feijão', 'unit': 'g', 'opening': 20000, 'reorder': 6000},
    {'id': 'I03', 'name': 'Legumes', 'unit': 'g', 'opening': 18000, 'reorder': 6000},
    {'id': 'I04', 'name': 'Batata', 'unit': 'g', 'opening': 22000, 'reorder': 5000},
    {'id': 'I05', 'name': 'Suco', 'unit': 'ml', 'opening': 24000, 'reorder': 6000},
]
RECIPES = {'P01': {'I01': 160, 'I02': 140}, 'P02': {'I01': 120, 'I03': 180}, 'P03': {'I04': 220}, 'P04': {'I05': 300}}
