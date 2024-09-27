from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Artifact, ArtifactContent


def create(
    session: Session,
    name: str,
    content: str,
    password: str | None = None,
    announcement: str | None = None,
    page: int = 0,
):
    artifact = session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
    )

    content_page = ArtifactContent(content=content, page=page)

    if artifact is None:
        artifact = Artifact(
            name=name,
            password=password,
            announcement=announcement,
            content=[content_page],
        )
    else:
        artifact.content.append(content_page)

    session.add(artifact)
    session.commit()


def access(session: Session, name: str, password: str | None = None):
    return session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
    )


def remove(session: Session, name: str, password: str | None = None):
    a = session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
    )
    session.delete(a)
    session.commit()
