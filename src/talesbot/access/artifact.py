from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..database.models import Artifact, ArtifactContent


async def create(
    session: AsyncSession,
    name: str,
    content: str,
    password: str | None = None,
    announcement: str | None = None,
    page: int = 0,
):
    artifact = await session.scalar(
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
    await session.commit()


async def access(session: AsyncSession, name: str, password: str | None = None):
    return await session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
        .options(joinedload(Artifact.content))
    )


async def remove(session: AsyncSession, name: str, password: str | None = None):
    a = session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
    )
    await session.delete(a)
    await session.commit()
