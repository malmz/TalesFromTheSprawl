from talesbot.database import artifact, SessionM, create_tables

create_tables()

with SessionM() as session:
    artifact.create(session, "coolthang", "more stuff2", page=2)

    t = artifact.access(session, "coolthang")

    print(t)
