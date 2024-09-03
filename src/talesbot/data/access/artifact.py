from sqlalchemy import select

from .. import Session
from ..schema import Artifact


def create(name: str, content: str):
    with Session.begin() as session:
        artifact = Artifact(name=name, content=content)
        session.add(artifact)

    return f"Created artifact {name}."


def access(name: str, password: str | None):
    stmt = select(Artifact).where(Artifact.name == name, Artifact.password == password)
    with Session() as session:
        artifact = session.scalars(stmt).first()
        if artifact is None:
            return (f'Error: entity "{name}" not found. Check the spelling.', None)

        return (artifact.content, artifact.announce)
