from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import random

REGISTER, ROLE_ASSIGNMENT, NIGHT, DAY, VOTING, END = range(6)

players = {}
roles = {}
alive_players = []
mafia = []
detective = None
victim = None
detected_player = None

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Привет! Добро пожаловать в игру 'Мафия'. Нажмите /join чтобы присоединиться к игре. Когда все готовы, нажмите /startgame чтобы начать.")
    return REGISTER

async def join(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if user.id not in players:
        players[user.id] = user.first_name
        await update.message.reply_text(f"{user.first_name} присоединился к игре!")
    else:
        await update.message.reply_text(f"{user.first_name}, вы уже зарегистрированы!")
    return REGISTER

async def startgame(update: Update, context: CallbackContext) -> int:
    global alive_players, mafia, detective

    if len(players) < 3:
        await update.message.reply_text("Недостаточно игроков для начала игры. Нужны минимум 3 игрока.")
        return REGISTER

    alive_players = list(players.keys())
    random.shuffle(alive_players)
    mafia = random.sample(alive_players, 1)
    detective = random.choice([p for p in alive_players if p not in mafia])

    roles[mafia[0]] = 'Мафия'
    roles[detective] = 'Комиссар'
    for p in alive_players:
        if p not in roles:
            roles[p] = 'Мирный житель'

    for player_id, role in roles.items():
        await context.bot.send_message(player_id, f"Ваша роль: {role}")

    await update.message.reply_text("Роли распределены. Ночь начинается...")
    return NIGHT

async def night(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if user.id in mafia:
        target_name = update.message.text
        target_id = get_player_id_by_name(target_name)
        
        if target_id and target_id in alive_players:
            global victim
            victim = target_id
            await context.bot.send_message(user.id, f"Вы выбрали убить {target_name}.")
        else:
            await context.bot.send_message(user.id, "Неправильный выбор цели. Попробуйте снова.")
            return NIGHT

    elif user.id == detective:
        suspect_name = update.message.text
        suspect_id = get_player_id_by_name(suspect_name)
        
        if suspect_id and suspect_id in alive_players:
            global detected_player
            detected_player = suspect_id
            role = roles[suspect_id]
            await context.bot.send_message(user.id, f"{suspect_name} - {role}.")
        else:
            await context.bot.send_message(user.id, "Неправильный выбор цели. Попробуйте снова.")
            return NIGHT
    if victim and detected_player:
        await update.message.reply_text("Ночь окончена. Переходим ко дню.")
        return day(update, context)

    return NIGHT

def get_player_id_by_name(name):
    for player_id, player_name in players.items():
        if player_name.lower() == name.lower():
            return player_id
    return None

async def day(update: Update, context: CallbackContext) -> int:
    global victim
    
    if victim in alive_players:
        await update.message.reply_text(f"{players[victim]} был убит!")
        alive_players.remove(victim)
    
    if check_game_end(update, context):
        return END
    await update.message.reply_text("Пришло время обсуждения! Начнется голосование через 1 минуту.")
    
    context.job_queue.run_once(start_voting, 60, context=update.message.chat_id)
    
    return DAY

async def start_voting(context: CallbackContext):
    job = context.job
    await context.bot.send_message(job.context, "Время обсуждения завершено. Начинается голосование! Напишите имя того, кого вы считаете мафией.")
    return VOTING

async def voting(update: Update, context: CallbackContext) -> int:
    voted_name = update.message.text
    voted_id = get_player_id_by_name(voted_name)
    
    if voted_id and voted_id in alive_players:
        await context.bot.send_message(update.message.chat_id, f"Голосование завершено! {players[voted_id]} был исключен из игры.")
        alive_players.remove(voted_id)
    else:
        await context.bot.send_message(update.message.chat_id, "Неправильное имя. Попробуйте снова.")
        return VOTING

    if check_game_end(update, context):
        return END

    return NIGHT

async def check_game_end(update: Update, context: CallbackContext) -> bool:
    if len(mafia) == 0:
        await update.message.reply_text("Мафия побеждена! Мирные победили!")
        return True
    elif len(mafia) >= len(alive_players) / 2:
        await update.message.reply_text("Мафия взяла контроль! Мафия победила!")
        return True
    return False

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Игра завершена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:

    application = Application.builder().token("тут крч твой токен бота").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER: [CommandHandler('join', join),
                       CommandHandler('startgame', startgame)],
            ROLE_ASSIGNMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, night)],
            NIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, night)],
            DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, voting)],
            VOTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, voting)],
            END: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
