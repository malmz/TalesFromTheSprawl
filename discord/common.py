import re

highest_ever_index = '___highest_ever'
system_role_name = 'system'
admin_role_name = 'admin'



gm_role_name = 'gm'

type_player = 'player'
type_shop = 'shop'

forbidden_content = '**'
forbidden_content_print = '\*\*'

transaction_collector = '___collector'
transaction_collected = '___collected'

coin = '¥'

# good-to-have emojis:
# ✅
# ❇️
# ❌
# 🟥
# 🔥
emoji_cancel = '❌'
emoji_open = '❇️'
emoji_accept = '✅'
emoji_green = '🟢'
emoji_red = '🔴'
emoji_green_book = '📗'
emoji_red_book = '📕'

emoji_alert = '❗'
emoji_unavail = '🚫'
emoji_unread = '💬'


# Roles
all_players_role_name = '251'
shop_role_start = 2300
player_personal_role_start = 2700
group_role_start = 2900

#personal_role_regex = re.compile(f'^27[0-9][0-9]$')
#shop_role_regex = re.compile(f'^23[0-9][0-9]$')

def is_shop_role(name : str):
	try:
		number = int(name)
		return number >= shop_role_start and number < player_personal_role_start
	except ValueError:
		return False

def is_player_role(name : str):
	try:
		number = int(name)
		return number >= player_personal_role_start and number < group_role_start
	except ValueError:
		return False


def is_group_role(name : str):
	try:
		number = int(name)
		return number >= group_role_start
	except ValueError:
		return False
