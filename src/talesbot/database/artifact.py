from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .models import Artifact, ArtifactContent


async def create(
    session: AsyncSession,
    name: str,
    content: str,
    password: str | None = None,
    announcement: str | None = None,
    page: int | None = None,
):
    artifact = await session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
        .options(joinedload(Artifact.content))
    )

    if artifact is None:
        artifact = Artifact(
            name=name, password=password, announcement=announcement, content=[]
        )
        session.add(artifact)

    artifact.announcement = announcement

    if page is None:
        page = len(artifact.content)

    content_page = next((p for p in artifact.content if p.page == page), None)
    if content_page is None:
        content_page = ArtifactContent(content=content, page=page)
        artifact.content.append(content_page)
    else:
        content_page.content = content

    await session.commit()
    return artifact, page


async def access(session: AsyncSession, name: str, password: str | None = None):
    return await session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
        .options(joinedload(Artifact.content))
    )


async def list(session: AsyncSession) -> Sequence[Artifact]:
    res = await session.scalars(select(Artifact))
    return res.all()


async def remove(session: AsyncSession, name: str, password: str | None = None):
    a = await session.scalar(
        select(Artifact)
        .where(Artifact.name == name)
        .where(Artifact.password == password)
    )
    await session.delete(a)
    await session.commit()
