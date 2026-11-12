# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add homepage_quotes table + seed en/es/fr from prior hardcoded list

Revision ID: homepage_quotes_001
Revises: fine_waivers_001
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "homepage_quotes_001"
down_revision: Union[str, None] = "fine_waivers_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_QUOTES_EN = [
    ("Nah, who gave yall a whole building full of free books?\nThat is wild.", "Druski"),
    (
        "The library is the worst group of people ever assembled in history. "
        "They're mean, conniving, rude, and extremely well-read, which makes them dangerous.",
        "Leslie Knope",
    ),
    (
        "I've been to this library before. I spent a lot of time here as a kid, "
        "hiding from bullies. You know what's a good book? Everything by Roald Dahl.",
        "Andy Dwyer",
    ),
    ("I am not a bookworm. I am a book dragon.", "Matilda Wormwood"),
    ("A room without books is like a body without a soul.", "The Doctor"),
    (
        "When you read a book as a child, it becomes a part of your identity "
        "in a way that no other reading in your whole life does.",
        "Meg Ryan, You've Got Mail",
    ),
    (
        "I declare after all there is no enjoyment like reading! "
        "How much sooner one tires of any thing than of a book!",
        "Caroline Bingley, Pride and Prejudice",
    ),
    ("So many books, so little time.", "Frank Zappa"),
    ("You don't need a reason to come in. That's the reason.", "Eunice Tibbett, cardholder since 1962"),
]

SEED_QUOTES_ES = [
    ("Siempre imaginé que el Paraíso sería algún tipo de biblioteca.", "Jorge Luis Borges"),
    (
        "El libro es la fuerza, es el valor, es el poder, es el alimento; "
        "antorcha del pensamiento y manantial del amor.",
        "Federico García Lorca",
    ),
    ("El que lee mucho y anda mucho, ve mucho y sabe mucho.", "Miguel de Cervantes, Don Quijote"),
    (
        "Los libros son espejos: sólo se ve en ellos lo que uno ya lleva dentro.",
        "Carlos Ruiz Zafón, La Sombra del Viento",
    ),
    (
        "Yo no estudio para escribir, ni menos para enseñar, "
        "sino sólo por ver si con estudiar ignoro menos.",
        "Sor Juana Inés de la Cruz",
    ),
]

SEED_QUOTES_FR = [
    (
        "Lire, c'est boire et manger. L'esprit qui ne lit pas maigrit comme le corps qui ne mange pas.",
        "Victor Hugo",
    ),
    (
        "La lecture est au seuil de la vie spirituelle ; "
        "elle peut nous y introduire : elle ne la constitue pas.",
        "Marcel Proust, Sur la lecture",
    ),
    (
        "L'étude a été pour moi le souverain remède contre les dégoûts de la vie, "
        "n'ayant jamais eu de chagrin qu'une heure de lecture n'ait dissipé.",
        "Montesquieu, Mes Pensées",
    ),
    (
        "J'ai commencé ma vie comme je la finirai sans doute : au milieu des livres.",
        "Jean-Paul Sartre, Les Mots",
    ),
    (
        "Fonder des bibliothèques, c'est encore construire des greniers publics, "
        "amasser des réserves contre un hiver de l'esprit.",
        "Marguerite Yourcenar, Mémoires d'Hadrien",
    ),
]


def upgrade() -> None:
    op.create_table(
        "homepage_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("locale", sa.String(length=8), nullable=False, index=True),
        sa.Column("quote_text", sa.Text(), nullable=False),
        sa.Column("attribution", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_homepage_quotes_locale_active_order",
        "homepage_quotes",
        ["locale", "is_active", "display_order"],
    )

    quotes_table = sa.table(
        "homepage_quotes",
        sa.column("locale", sa.String),
        sa.column("quote_text", sa.Text),
        sa.column("attribution", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("display_order", sa.Integer),
    )

    rows = []
    for locale, seed in (("en", SEED_QUOTES_EN), ("es", SEED_QUOTES_ES), ("fr", SEED_QUOTES_FR)):
        for idx, (text, author) in enumerate(seed):
            rows.append(
                {
                    "locale": locale,
                    "quote_text": text,
                    "attribution": author,
                    "is_active": True,
                    "display_order": idx,
                }
            )

    if rows:
        op.bulk_insert(quotes_table, rows)


def downgrade() -> None:
    op.drop_index("ix_homepage_quotes_locale_active_order", table_name="homepage_quotes")
    op.drop_table("homepage_quotes")
