from sqlalchemy import update
from sqlalchemy.orm import Session

from ..schema import Sequence


def next_player(session: Session):
    """seq = session.scalar(select(Sequence).where(Sequence.id == "player_index"))
    if seq is None:
        seq = Sequence(id="player_index",  value = 2700)
        session.add(seq)

    seq.value += 1
    session.commit()"""

    val = session.scalar(
        update(Sequence)
        .where(Sequence.id == "player_index")
        .values(value=Sequence.value + 1)
        .returning(Sequence.value)
    )

    if val is None:
        raise Exception("no player index")
