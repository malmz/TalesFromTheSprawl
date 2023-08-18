from peewee import *


database = SqliteDatabase("data.sqlite")


def create_tables():
    with database:
        database.create_tables(
            [Player, Shop, Employee, Group, GroupMember, Handle, PlayerHandle]
        )


class BaseModel(Model):
    class Meta:
        database = database


class Player(BaseModel):
    player_id = IntegerField(unique=True)
    discord_id = TextField(unique=True)

    def handles(self):
        return (
            Handle.select(Handle)
            .join(PlayerHandle)
            .join(Player)
            .where(PlayerHandle.player == self)
        )


class Shop(BaseModel):
    name = TextField(unique=True)


class Employee(BaseModel):
    player = ForeignKeyField(Player)
    shop = ForeignKeyField(Shop)


class Group(BaseModel):
    name = TextField(unique=True)


class GroupMember(BaseModel):
    player = ForeignKeyField(Player)
    group = ForeignKeyField(Group)


class Handle(BaseModel):
    name = TextField(unique=True)
    balance = IntegerField(default=0)


class PlayerHandle(BaseModel):
    player = ForeignKeyField(Player)
    handle = ForeignKeyField(Handle)
