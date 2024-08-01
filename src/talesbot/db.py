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


class Handle(BaseModel):
	name = TextField(unique=True)
	balance = IntegerField(default=0)


class Player(BaseModel):
	discord_id = TextField(unique=True)
	active_handle = ForeignKeyField(Handle)


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


class PlayerHandle(BaseModel):
	player = ForeignKeyField(Player, backref="handles")
	handle = ForeignKeyField(Handle, backref="players")
