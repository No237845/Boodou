"""Simulateur du bot en ligne de commande, sans WhatsApp ni SMS.

    python -m scripts.bot_sim                      # mode interactif
    python -m scripts.bot_sim "Bonjour" 1 1 3 5 "Il y a eu une attaque"   # script

Utile pour tester le moteur de menu et les textes avant de brancher Meta.
"""

import sys

from app import migrations
from app.bot import engine
from app.db import Base, SessionLocal, engine as db_engine
from app.models import Channel
from app.seed import seed_resources

PHONE = "22670000000"  # numéro fictif, haché par le moteur


def say(text: str) -> None:
    with SessionLocal() as db:
        for reply in engine.handle(db, Channel.WHATSAPP, PHONE, text):
            print(f"\n🤖 {reply}")


def main() -> None:
    Base.metadata.create_all(bind=db_engine)
    migrations.run(db_engine)
    with SessionLocal() as db:
        seed_resources(db)
    engine.reset_session(PHONE)

    args = sys.argv[1:]
    if args:
        for msg in args:
            print(f"\n👤 {msg}")
            say(msg)
        return

    print("Tapez vos messages (Ctrl+C pour quitter).")
    say("Bonjour")
    while True:
        try:
            say(input("\n👤 "))
        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    main()
